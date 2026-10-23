import pytest
from routing_engine.services.risk_engine import (
    RiskLevel,
    classify_wind,
    classify_rain,
    classify_snow,
    apply_cargo_overrides,
    evaluate_checkpoint_risk,
)


class TestWindClassification:
    def test_wind_low(self):
        assert classify_wind(0.0) == RiskLevel.LOW
        assert classify_wind(15.5) == RiskLevel.LOW
        assert classify_wind(24.9) == RiskLevel.LOW

    def test_wind_moderate_boundary(self):
        # Exactly 25 mph should be Moderate
        assert classify_wind(25.0) == RiskLevel.MODERATE
        assert classify_wind(30.0) == RiskLevel.MODERATE
        assert classify_wind(34.9) == RiskLevel.MODERATE

    def test_wind_high_boundary(self):
        # Exactly 35 mph should be High
        assert classify_wind(35.0) == RiskLevel.HIGH
        assert classify_wind(40.0) == RiskLevel.HIGH
        assert classify_wind(44.9) == RiskLevel.HIGH

    def test_wind_severe_boundary(self):
        # Exactly 45 mph should be Severe
        assert classify_wind(45.0) == RiskLevel.SEVERE
        assert classify_wind(50.0) == RiskLevel.SEVERE
        assert classify_wind(54.9) == RiskLevel.SEVERE

    def test_wind_no_travel_boundary(self):
        # Exactly 55 mph and above is No Travel
        assert classify_wind(55.0) == RiskLevel.NO_TRAVEL
        assert classify_wind(65.0) == RiskLevel.NO_TRAVEL

    def test_negative_wind_raises(self):
        with pytest.raises(ValueError):
            classify_wind(-5.0)


class TestRainClassification:
    def test_rain_low(self):
        assert classify_rain(0.0) == RiskLevel.LOW
        assert classify_rain(0.05) == RiskLevel.LOW
        assert classify_rain(0.09) == RiskLevel.LOW

    def test_rain_moderate_boundary(self):
        # Exactly 0.10 is Moderate
        assert classify_rain(0.10) == RiskLevel.MODERATE
        assert classify_rain(0.20) == RiskLevel.MODERATE
        assert classify_rain(0.24) == RiskLevel.MODERATE

    def test_rain_high_boundary(self):
        # Exactly 0.25 is High
        assert classify_rain(0.25) == RiskLevel.HIGH
        assert classify_rain(0.40) == RiskLevel.HIGH
        assert classify_rain(0.49) == RiskLevel.HIGH

    def test_rain_severe_boundary(self):
        # Exactly 0.50 is Severe, up to 1.00
        assert classify_rain(0.50) == RiskLevel.SEVERE
        assert classify_rain(0.75) == RiskLevel.SEVERE
        assert classify_rain(1.00) == RiskLevel.SEVERE

    def test_rain_no_travel_boundary(self):
        # > 1.00 is No Travel
        assert classify_rain(1.01) == RiskLevel.NO_TRAVEL
        assert classify_rain(2.50) == RiskLevel.NO_TRAVEL

    def test_negative_rain_raises(self):
        with pytest.raises(ValueError):
            classify_rain(-0.1)


class TestSnowClassification:
    def test_snow_low(self):
        assert classify_snow(0.0) == RiskLevel.LOW
        assert classify_snow(0.2) == RiskLevel.LOW
        assert classify_snow(0.49) == RiskLevel.LOW

    def test_snow_moderate_boundary(self):
        # Exactly 0.5 is Moderate
        assert classify_snow(0.5) == RiskLevel.MODERATE
        assert classify_snow(0.8) == RiskLevel.MODERATE
        assert classify_snow(0.99) == RiskLevel.MODERATE

    def test_snow_high_boundary(self):
        # Exactly 1.0 is High
        assert classify_snow(1.0) == RiskLevel.HIGH
        assert classify_snow(1.5) == RiskLevel.HIGH
        assert classify_snow(1.99) == RiskLevel.HIGH

    def test_snow_severe_boundary(self):
        # Exactly 2.0 is Severe, up to 3.0
        assert classify_snow(2.0) == RiskLevel.SEVERE
        assert classify_snow(2.8) == RiskLevel.SEVERE
        assert classify_snow(3.0) == RiskLevel.SEVERE

    def test_snow_no_travel_boundary(self):
        # > 3.0 is No Travel
        assert classify_snow(3.01) == RiskLevel.NO_TRAVEL
        assert classify_snow(5.0) == RiskLevel.NO_TRAVEL

    def test_negative_snow_raises(self):
        with pytest.raises(ValueError):
            classify_snow(-1.0)


class TestCargoWeightOverrides:
    def test_wind_ge_55_no_travel_for_any_load(self):
        # Rule: >=55 mph -> No Travel for any load
        risk, reason = apply_cargo_overrides(RiskLevel.NO_TRAVEL, 55.0, 10000.0)
        assert risk == RiskLevel.NO_TRAVEL
        assert reason is not None

        risk, reason = apply_cargo_overrides(RiskLevel.NO_TRAVEL, 60.0, 50000.0)
        assert risk == RiskLevel.NO_TRAVEL

    def test_wind_45_54_with_cargo_thresholds(self):
        # Rule: 45-54 mph + >30,000 lb -> No Travel
        # At exactly 30,000 lb, it should NOT trigger No Travel (remains Severe)
        risk, reason = apply_cargo_overrides(RiskLevel.SEVERE, 48.0, 30000.0)
        assert risk == RiskLevel.SEVERE
        assert reason is None

        # Just above 30,000 lb -> triggers No Travel
        risk, reason = apply_cargo_overrides(RiskLevel.SEVERE, 48.0, 30001.0)
        assert risk == RiskLevel.NO_TRAVEL
        assert "No Travel override" in reason

        # Well above 30,000 lb -> No Travel
        risk, reason = apply_cargo_overrides(RiskLevel.SEVERE, 50.0, 42000.0)
        assert risk == RiskLevel.NO_TRAVEL

        # Under 30,000 lb -> remains Severe
        risk, reason = apply_cargo_overrides(RiskLevel.SEVERE, 48.0, 25000.0)
        assert risk == RiskLevel.SEVERE

    def test_wind_35_44_with_cargo_thresholds(self):
        # Rule: 35-44 mph + >40,000 lb -> Severe
        # At exactly 40,000 lb, it should NOT trigger Severe (remains High)
        risk, reason = apply_cargo_overrides(RiskLevel.HIGH, 38.0, 40000.0)
        assert risk == RiskLevel.HIGH
        assert reason is None

        # Just above 40,000 lb -> triggers Severe
        risk, reason = apply_cargo_overrides(RiskLevel.HIGH, 38.0, 40001.0)
        assert risk == RiskLevel.SEVERE
        assert "Severe override" in reason

        # Under 40,000 lb -> remains High
        risk, reason = apply_cargo_overrides(RiskLevel.HIGH, 42.0, 35000.0)
        assert risk == RiskLevel.HIGH


class TestCombinedRiskEvaluation:
    def test_mixed_hazards_takes_highest_risk(self):
        # Low wind (10 mph), Moderate rain (0.15 in/hr), Low snow (0.0) -> Moderate
        res = evaluate_checkpoint_risk(10.0, 0.15, 0.0, 35000.0)
        assert res["effective_risk"] == RiskLevel.MODERATE.value
        assert res["risk_score"] == 2.0

        # High wind (38 mph), Severe snow (2.5 in/hr) -> Severe
        res2 = evaluate_checkpoint_risk(38.0, 0.0, 2.5, 30000.0)
        assert res2["effective_risk"] == RiskLevel.SEVERE.value
        assert res2["risk_score"] == 4.0

    def test_no_travel_dominance(self):
        # Low wind (5 mph), Low snow (0.0), No Travel rain (1.2 in/hr) -> No Travel
        res = evaluate_checkpoint_risk(5.0, 1.2, 0.0, 20000.0)
        assert res["effective_risk"] == RiskLevel.NO_TRAVEL.value
        assert res["risk_score"] == 5.0
