import pytest
from datetime import datetime, timezone, timedelta
from routing_engine.services.weather import (
    _parse_iso_to_dt,
    _find_nearest_hour_index,
    enrich_checkpoints_with_weather,
)
from routing_engine.services.risk_engine import RiskLevel, RISK_ORDINAL_MAP, evaluate_checkpoint_risk
from routing_engine.services.recommender import calculate_route_metrics


class TestTimestampAlignment:
    def test_nearest_hour_alignment(self):
        forecast_times = [
            "2026-10-24T12:00",
            "2026-10-24T13:00",
            "2026-10-24T14:00",
            "2026-10-24T15:00",
            "2026-10-24T16:00",
        ]

        # Case A: Checkpoint ETA is 14:10 UTC -> should pick 14:00 (index 2)
        dt_1410 = datetime(2026, 10, 24, 14, 10, tzinfo=timezone.utc)
        idx_a = _find_nearest_hour_index(dt_1410, forecast_times)
        assert idx_a == 2
        assert forecast_times[idx_a] == "2026-10-24T14:00"

        # Case B: Checkpoint ETA is 14:38 UTC -> should pick 15:00 (index 3, diff 22 min vs 38 min)
        dt_1438 = datetime(2026, 10, 24, 14, 38, tzinfo=timezone.utc)
        idx_b = _find_nearest_hour_index(dt_1438, forecast_times)
        assert idx_b == 3
        assert forecast_times[idx_b] == "2026-10-24T15:00"

    def test_iso_parsing_utc_handling(self):
        dt_z = _parse_iso_to_dt("2026-10-24T08:00:00Z")
        assert dt_z.tzinfo == timezone.utc
        assert dt_z.hour == 8

        dt_offset = _parse_iso_to_dt("2026-10-24T08:00:00+00:00")
        assert dt_offset.tzinfo == timezone.utc
        assert dt_offset.hour == 8


class TestMissingForecastData:
    def test_empty_checkpoints_returns_empty(self):
        assert enrich_checkpoints_with_weather([], cargo_weight_lbs=42000, departure_time_iso="2026-10-24T08:00:00Z") == []

    def test_missing_weather_evaluates_to_unknown_not_silently_low(self):
        from unittest.mock import patch
        # Synthetic checkpoint with no live external connection or cached weather
        checkpoints = [
            {
                "index": 0,
                "distance_from_origin_miles": 0.0,
                "segment_distance_miles": 10.0,
                "lat": 37.0,
                "lon": -107.0,
                "eta": "2026-10-24T08:00:00Z",
                "elapsed_hours": 0.0,
            }
        ]
        with patch("routing_engine.services.weather.cache.get", return_value=[]), \
             patch("routing_engine.services.weather.requests.get", side_effect=Exception("API offline")):
            res = enrich_checkpoints_with_weather(checkpoints, cargo_weight_lbs=42000, departure_time_iso="2026-10-24T08:00:00Z")
            assert len(res) == 1
            cp = res[0]
            assert "weather" in cp
            # Crucial safety check: missing forecast data must be explicitly represented as Unknown, not silently Low risk
            assert cp["effective_risk"] == RiskLevel.UNKNOWN.value
            assert cp["effective_risk"] != RiskLevel.LOW.value
            assert cp["weather"]["data_status"] == "missing"
            assert cp["weather"]["forecast_timestamp"] == "Unavailable"

    def test_out_of_range_eta_evaluates_to_unknown(self):
        from unittest.mock import patch
        # Mock weather provider returning a 3-day window from Oct 24 to Oct 27
        mock_raw = [
            {
                "hourly": {
                    "time": ["2026-10-24T00:00", "2026-10-24T01:00", "2026-10-27T00:00"],
                    "temperature_2m": [50.0, 50.0, 50.0],
                    "precipitation": [0.0, 0.0, 0.0],
                    "snowfall": [0.0, 0.0, 0.0],
                    "wind_speed_10m": [5.0, 5.0, 5.0],
                }
            }
        ]
        # ETA is Nov 10, 2026 (two weeks beyond forecast horizon)
        checkpoints = [
            {
                "index": 0,
                "distance_from_origin_miles": 0.0,
                "segment_distance_miles": 10.0,
                "lat": 37.0,
                "lon": -107.0,
                "eta": "2026-11-10T12:00:00Z",
                "elapsed_hours": 0.0,
            }
        ]
        with patch("routing_engine.services.weather.cache.get", return_value=mock_raw):
            res = enrich_checkpoints_with_weather(checkpoints, cargo_weight_lbs=42000, departure_time_iso="2026-10-24T00:00:00Z")
            assert len(res) == 1
            cp = res[0]
            # Must not silently use the nearest hour and classify as Low
            assert cp["effective_risk"] == RiskLevel.UNKNOWN.value
            assert cp["effective_risk"] != RiskLevel.LOW.value
            assert cp["weather"]["data_status"] == "out_of_range"


class TestDistanceWeightedAverageRisk:
    def test_all_low_risk_route_is_strictly_1_00(self):
        # Simulating Farmington to Durango: 6 checkpoints, all Low risk (1.0)
        cps = [
            {"index": 0, "segment_distance_miles": 5.0, "effective_risk": "Low", "risk_score": 1.0},
            {"index": 1, "segment_distance_miles": 10.0, "effective_risk": "Low", "risk_score": 1.0},
            {"index": 2, "segment_distance_miles": 10.0, "effective_risk": "Low", "risk_score": 1.0},
            {"index": 3, "segment_distance_miles": 10.0, "effective_risk": "Low", "risk_score": 1.0},
            {"index": 4, "segment_distance_miles": 11.05, "effective_risk": "Low", "risk_score": 1.0},
            {"index": 5, "segment_distance_miles": 6.05, "effective_risk": "Low", "risk_score": 1.0},
        ]
        total_dist = 52.1
        metrics = calculate_route_metrics("r1", "US-550 N", total_dist, 1.25, cps, {})
        assert metrics["average_risk_score"] == 1.00
        assert metrics["risk_mileage"]["low_miles"] == 52.1
        assert metrics["risk_mileage"]["total_accounted_miles"] == 52.1
        assert metrics["overall_classification"] == "Low"

    def test_mixed_segment_weighted_average(self):
        # 30 miles Low (score 1.0) + 10 miles Moderate (score 2.0)
        # Weighted sum = 30*1.0 + 10*2.0 = 50.0
        # Avg = 50.0 / 40.0 = 1.25
        cps = [
            {"index": 0, "segment_distance_miles": 30.0, "effective_risk": "Low", "risk_score": 1.0},
            {"index": 1, "segment_distance_miles": 10.0, "effective_risk": "Moderate", "risk_score": 2.0},
        ]
        metrics = calculate_route_metrics("r2", "Mixed Route", 40.0, 1.0, cps, {})
        assert metrics["average_risk_score"] == 1.25
        assert metrics["risk_mileage"]["low_miles"] == 30.0
        assert metrics["risk_mileage"]["moderate_miles"] == 10.0
        assert metrics["overall_classification"] == "Moderate"


class TestHeatmapFormulaLogic:
    def test_heatmap_formula_calm_vs_severe(self):
        # Replicating frontend getHeatmapColorAndOpacity logic in Python for mathematical auditing
        def compute_heatmap(wind_mph, rain_in_hr, snow_in_hr, seg_miles=25):
            wind_score = min(wind_mph / 55.0, 1.0)
            rain_score = min(rain_in_hr / 1.0, 1.0)
            snow_score = min(snow_in_hr / 3.0, 1.0)
            max_hazard = max(wind_score, rain_score, snow_score)

            base_radius = max(12000, min(25000, seg_miles * 1200))

            if wind_mph >= 55.0 or rain_in_hr > 1.0 or snow_in_hr > 3.0:
                return "#5c1319", min(0.70, 0.52 + 0.18 * max_hazard), base_radius
            elif wind_mph >= 45.0 or rain_in_hr >= 0.5 or snow_in_hr >= 2.0:
                return "#d93025", min(0.60, 0.40 + 0.15 * max_hazard), base_radius
            elif wind_mph >= 35.0 or rain_in_hr >= 0.25 or snow_in_hr >= 1.0:
                return "#ea8600", min(0.48, 0.30 + 0.12 * max_hazard), base_radius
            elif wind_mph >= 25.0 or rain_in_hr >= 0.10 or snow_in_hr >= 0.5:
                return "#f9ab00", min(0.38, 0.20 + 0.10 * max_hazard), base_radius
            else:
                return "#34a853", 0.06 + 0.08 * max_hazard, base_radius

        # 1. Calm Farmington NM Checkpoint #4: wind=8.4 mph, rain=0, snow=0, segment=10 mi
        color_calm, opacity_calm, radius_calm = compute_heatmap(8.4, 0.0, 0.0, 10.0)
        assert color_calm == "#34a853"
        # Opacity should be subtle and transparent (< 0.10)
        assert 0.06 <= opacity_calm < 0.10
        # Radius for 10-mile segment should be bounded to 12,000 meters
        assert radius_calm == 12000

        # 2. Severe rain event: rain=0.65 in/hr
        color_sev, opacity_sev, radius_sev = compute_heatmap(15.0, 0.65, 0.0, 25.0)
        assert color_sev == "#d93025"
        assert opacity_sev >= 0.40
        assert radius_sev == 25000

        # 3. No Travel storm: wind=60 mph
        color_nt, opacity_nt, radius_nt = compute_heatmap(60.0, 0.0, 0.0, 25.0)
        assert color_nt == "#5c1319"
        assert opacity_nt >= 0.52
