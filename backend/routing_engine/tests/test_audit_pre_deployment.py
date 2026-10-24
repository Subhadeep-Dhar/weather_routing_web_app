import pytest
from rest_framework.test import APIClient
from routing_engine.services.geocoding import geocode_address
from routing_engine.services.routing import METERS_TO_MILES
from routing_engine.services.risk_engine import evaluate_checkpoint_risk, RiskLevel
from routing_engine.services.recommender import calculate_route_metrics, rank_and_recommend_routes
from routing_engine.services.truck_eta_model import calculate_defensible_truck_eta, haversine_distance_miles


@pytest.fixture
def api_client():
    return APIClient()


class TestPreDeploymentAudit:
    """
    Regression tests for Spotter SafeRoute Pre-Deployment Correctness and Default UX Audit.
    """

    def test_geocoding_siliguri_and_gangtok_coordinates(self):
        """
        Verify that the actual geocoding service resolves Siliguri and Gangtok
        to their authentic geographic coordinates in Northeast India.
        """
        siliguri_res = geocode_address("Siliguri, West Bengal, India", limit=1)
        assert len(siliguri_res) > 0, "Siliguri must resolve via geocoding service"
        siliguri = siliguri_res[0]
        # Siliguri is located around 26.71°N, 88.43°E
        assert 26.5 <= siliguri["lat"] <= 27.0, f"Unexpected latitude for Siliguri: {siliguri['lat']}"
        assert 88.2 <= siliguri["lon"] <= 88.6, f"Unexpected longitude for Siliguri: {siliguri['lon']}"

        gangtok_res = geocode_address("Gangtok, Sikkim, India", limit=1)
        assert len(gangtok_res) > 0, "Gangtok must resolve via geocoding service"
        gangtok = gangtok_res[0]
        # Gangtok is located around 27.33°N, 88.61°E
        assert 27.1 <= gangtok["lat"] <= 27.5, f"Unexpected latitude for Gangtok: {gangtok['lat']}"
        assert 88.4 <= gangtok["lon"] <= 88.8, f"Unexpected longitude for Gangtok: {gangtok['lon']}"

    def test_distance_and_duration_unit_conversions(self):
        """
        Verify conversion formulas between meters/miles and seconds/hours.
        Must strictly adhere to exact international standards.
        """
        # 1 international mile is defined as 1609.344 meters exactly
        exact_meters = 1609.344
        miles = exact_meters * METERS_TO_MILES
        assert round(miles, 6) == 1.000000

        # 100 km = 100,000 meters = 62.1371 miles
        meters_100km = 100000.0
        miles_100km = meters_100km * METERS_TO_MILES
        assert round(miles_100km, 2) == 62.14

        # Duration seconds to hours conversion
        dur_seconds = 7200.0
        dur_hours = dur_seconds / 3600.0
        assert dur_hours == 2.0

        dur_seconds_mountain = 16200.0  # 4.5 hours
        assert (dur_seconds_mountain / 3600.0) == 4.5

    def test_cargo_overrides_with_heavy_load_preset(self):
        """
        Verify that cargo weight of 42,000 lbs (Heavy Preset used for Siliguri-Gangtok)
        triggers the assessment's required cargo-weight overrides:
        - Wind 35-44 mph AND cargo > 40,000 lb -> Severe override (overriding High).
        - Wind 45-54 mph AND cargo > 30,000 lb -> No Travel override.
        """
        cargo_weight = 42000.0

        # Scenario 1: Wind 38 mph (normally High: 35-44 mph) with 42k lb load
        eval_severe = evaluate_checkpoint_risk(
            wind_mph=38.0,
            rain_in_hr=0.0,
            snow_in_hr=0.0,
            cargo_weight_lbs=cargo_weight,
        )
        assert eval_severe["effective_risk"] == RiskLevel.SEVERE.value
        assert eval_severe["cargo_override_reason"] is not None
        assert "Severe" in eval_severe["cargo_override_reason"]

        # Scenario 2: Wind 48 mph (normally Severe: 45-54 mph) with 42k lb load
        eval_no_travel = evaluate_checkpoint_risk(
            wind_mph=48.0,
            rain_in_hr=0.0,
            snow_in_hr=0.0,
            cargo_weight_lbs=cargo_weight,
        )
        assert eval_no_travel["effective_risk"] == RiskLevel.NO_TRAVEL.value
        assert eval_no_travel["cargo_override_reason"] is not None
        assert "No Travel" in eval_no_travel["cargo_override_reason"]

    def test_unknown_weather_handling_and_no_safest_badge(self):
        """
        Verify that when weather forecasts are incomplete or unavailable:
        - Checkpoints are classified as Unknown.
        - Numerical average risk is not misleadingly calculated as 0.00.
        - Recommendation rationale does not label the route as "Safest route".
        """
        checkpoints = [
            {
                "index": 0,
                "distance_from_origin_miles": 0.0,
                "segment_distance_miles": 10.0,
                "lat": 26.7164,
                "lon": 88.4310,
                "eta": "2026-10-24T12:00:00Z",
                "elapsed_hours": 0.0,
                "weather": {
                    "wind_speed_mph": None,
                    "rain_intensity_in_hr": None,
                    "snow_intensity_in_hr": None,
                    "temperature_f": None,
                    "forecast_timestamp": "unavailable",
                    "data_status": "missing",
                },
                "hazard_classifications": {
                    "wind": "Unknown",
                    "effective_wind": "Unknown",
                    "rain": "Unknown",
                    "snow": "Unknown",
                },
                "cargo_override_applied": None,
                "effective_risk": "Unknown",
                "risk_score": None,
                "timeline_48h": [],
            },
            {
                "index": 1,
                "distance_from_origin_miles": 10.0,
                "segment_distance_miles": 10.0,
                "lat": 26.8500,
                "lon": 88.4800,
                "eta": "2026-10-24T12:30:00Z",
                "elapsed_hours": 0.5,
                "weather": {
                    "wind_speed_mph": None,
                    "rain_intensity_in_hr": None,
                    "snow_intensity_in_hr": None,
                    "temperature_f": None,
                    "forecast_timestamp": "unavailable",
                    "data_status": "missing",
                },
                "hazard_classifications": {
                    "wind": "Unknown",
                    "effective_wind": "Unknown",
                    "rain": "Unknown",
                    "snow": "Unknown",
                },
                "cargo_override_applied": None,
                "effective_risk": "Unknown",
                "risk_score": None,
                "timeline_48h": [],
            },
        ]

        metrics = calculate_route_metrics(
            route_id="route_1",
            name="Via NH 10",
            distance_miles=20.0,
            duration_hours=1.2,
            checkpoints=checkpoints,
            geometry={"type": "LineString", "coordinates": [[88.431, 26.716], [88.480, 26.850]]},
        )

        assert metrics["average_risk_score"] is None, "Average risk must be None (never 0.00) when all checkpoints are Unknown"
        assert metrics["weather_coverage_pct"] == 0.0
        assert metrics["risk_mileage"]["unknown_miles"] == 20.0
        assert metrics["is_weather_complete"] is False

        # Rank routes
        ranked = rank_and_recommend_routes([metrics])
        recs = ranked[0]["recommendation_reasons"]
        reasons_text = " ".join(recs)

        # Must NOT claim "Safest route"
        assert "Safest route" not in reasons_text
        assert "Incomplete weather coverage" in reasons_text or "unavailable" in reasons_text

    @pytest.mark.django_db
    def test_live_siliguri_to_gangtok_trip_analysis(self, api_client):
        """
        End-to-end integration test of the default trip (Siliguri -> Gangtok, 42k lb, 10 mi interval)
        against the Django TripAnalysisView.
        """
        payload = {
            "origin": "Siliguri, West Bengal, India",
            "destination": "Gangtok, Sikkim, India",
            "departure_time": "2026-10-24T12:00:00Z",
            "cargo_weight_lbs": 42000,
            "checkpoint_interval_miles": 10,
        }
        resp = api_client.post("/api/routes/analyze/", payload, format="json")
        assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.json()}"
        data = resp.json()

        assert "routes" in data
        assert len(data["routes"]) >= 1, "Should return at least 1 route option"
        assert data["request_params"]["checkpoint_interval_miles"] == 10.0
        assert data["request_params"]["cargo_weight_lbs"] == 42000.0

        top_route = data["routes"][0]
        # Siliguri to Gangtok road distance is typically around 65-80 miles (approx 105-130 km)
        assert 50.0 <= top_route["distance_miles"] <= 120.0, f"Route distance out of expected range: {top_route['distance_miles']} mi"

        # Checkpoints sampling: at 10 miles frequency on ~70 mi route, should have 4 to 10 checkpoints
        assert top_route["checkpoint_count"] >= 3

        # Distance reconciliation test
        rm = top_route["risk_mileage"]
        sum_cats = (
            rm["low_miles"]
            + rm["moderate_miles"]
            + rm["high_miles"]
            + rm["severe_miles"]
            + rm["no_travel_miles"]
            + rm["unknown_miles"]
        )
        assert abs(top_route["distance_miles"] - sum_cats) <= 0.1, (
            f"Distance reconciliation mismatch: total={top_route['distance_miles']}, sum={sum_cats}"
        )

        # Regression check: Siliguri -> Gangtok must NOT return 1.47 hours!
        # Modeled truck transit time must be in realistic mountain commercial crawl range (4.5 - 6.5 hours)
        assert 4.5 <= top_route["duration_hours"] <= 7.0, (
            f"Implausible truck duration for Siliguri-Gangtok: {top_route['duration_hours']} hrs (expected 4.5-7.0 hrs)"
        )
        # Raw OSRM car baseline must be preserved separately for transparency
        assert "duration_raw_osrm_hours" in top_route
        assert 1.2 <= top_route["duration_raw_osrm_hours"] <= 2.0, (
            f"Raw OSRM baseline duration unexpected: {top_route['duration_raw_osrm_hours']} hrs"
        )
        # Context-aware disclaimer type must be 'mountain'
        assert top_route.get("terrain_classification") == "mountain"
        assert top_route.get("disclaimer_type") == "mountain"

        # Checkpoints ETAs must advance over the modeled truck transit time
        first_cp = top_route["checkpoints"][0]
        last_cp = top_route["checkpoints"][-1]
        assert first_cp["elapsed_hours"] == 0.0
        assert 4.5 <= last_cp["elapsed_hours"] <= 7.0, (
            f"Last checkpoint arrival must reflect truck transit duration: {last_cp['elapsed_hours']} hrs"
        )

    def test_defensible_truck_eta_siliguri_gangtok_regression(self):
        """
        Unit regression test for the Siliguri-Gangtok mountain corridor.
        Tests that high sinuosity and 1500m elevation gain govern truck speeds to 22-25 km/h.
        """
        # Distance: ~70 miles (113 km), Raw OSRM: 5293 seconds (1.47 hrs)
        res = calculate_defensible_truck_eta(
            distance_miles=70.5,
            raw_duration_seconds=5293.0,
            origin_lat=26.7271,
            origin_lon=88.3953,
            dest_lat=27.3314,
            dest_lon=88.6138,
            cargo_weight_lbs=42000.0,
        )
        assert res["duration_raw_osrm_hours"] == 1.47
        assert 4.8 <= res["duration_truck_hours"] <= 5.5, f"Truck duration out of expected range: {res['duration_truck_hours']} hrs"
        assert 12.0 <= res["average_truck_speed_mph"] <= 16.0
        assert 20.0 <= res["average_truck_speed_kmh"] <= 26.0
        assert res["terrain_classification"] == "mountain"
        assert res["disclaimer_type"] == "mountain"
        assert len(res["model_assumptions"]) >= 2

    def test_truck_eta_cargo_weight_governing_rule(self):
        """
        Verify that cargo weight adjusts hill-climbing speed and transit time according to documented physics:
        - Heavy load (>40k lbs): governed to ~24 km/h climb.
        - Light load (<30k lbs): governed to ~32 km/h climb.
        """
        # Test identical mountain geometry with 42,000 lb vs 15,000 lb
        res_heavy = calculate_defensible_truck_eta(
            distance_miles=70.0,
            raw_duration_seconds=5300.0,
            origin_lat=26.7271,
            origin_lon=88.3953,
            dest_lat=27.3314,
            dest_lon=88.6138,
            cargo_weight_lbs=42000.0,
        )
        res_light = calculate_defensible_truck_eta(
            distance_miles=70.0,
            raw_duration_seconds=5300.0,
            origin_lat=26.7271,
            origin_lon=88.3953,
            dest_lat=27.3314,
            dest_lon=88.6138,
            cargo_weight_lbs=15000.0,
        )
        # Heavy load must take longer than light load on steep grades
        assert res_heavy["duration_truck_hours"] > res_light["duration_truck_hours"]
        assert res_heavy["average_truck_speed_kmh"] < res_light["average_truck_speed_kmh"]

    def test_truck_eta_flat_interstate_chicago_indianapolis(self):
        """
        Verify that on flat interstate corridors, the model applies fleet speed limiters
        and standard commercial safety buffers rather than mountain crawl speeds.
        """
        res = calculate_defensible_truck_eta(
            distance_miles=180.0,
            raw_duration_seconds=10800.0,  # 3.0 hrs (60 mph car baseline)
            origin_lat=41.8781,
            origin_lon=-87.6298,
            dest_lat=39.7684,
            dest_lon=-86.1581,
            cargo_weight_lbs=42000.0,
        )
        assert res["terrain_classification"] == "flat"
        assert res["disclaimer_type"] == "highway"
        # 180 miles at ~55-57 mph governed speed + rest buffer -> ~3.3 - 4.2 hours
        assert 3.2 <= res["duration_truck_hours"] <= 4.5
        assert res["average_truck_speed_mph"] >= 40.0

    def test_truck_eta_ghat_corridor_bengaluru_mangaluru(self):
        """
        Verify that an inter-city route crossing a mountain pass (e.g. Western Ghats)
        is classified as ghat_corridor, separating ghat switchback crawl from highway cruising.
        """
        res = calculate_defensible_truck_eta(
            distance_miles=226.7,
            raw_duration_seconds=17140.0,  # 4.76 hrs car baseline
            origin_lat=12.9716,
            origin_lon=77.5946,
            dest_lat=12.9141,
            dest_lon=74.8560,
            cargo_weight_lbs=42000.0,
        )
        assert res["terrain_classification"] == "ghat_corridor"
        assert res["disclaimer_type"] == "ghat"
        # Real-world truck transit time across Deccan plateau + Shiradi Ghat is 7.5 - 9.0 hrs
        assert 7.5 <= res["duration_truck_hours"] <= 9.2
        assert 24.0 <= res["average_truck_speed_mph"] <= 32.0
