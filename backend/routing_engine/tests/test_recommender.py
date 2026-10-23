from typing import Optional
from routing_engine.services.recommender import (
    calculate_route_metrics,
    rank_and_recommend_routes,
)
from routing_engine.services.risk_engine import RiskLevel


def make_checkpoint(idx: int, dist: float, seg_dist: float, risk_level: RiskLevel, risk_score: Optional[float]):
    return {
        "index": idx,
        "distance_from_origin_miles": dist,
        "segment_distance_miles": seg_dist,
        "lat": 40.0,
        "lon": -80.0,
        "eta": "2026-10-24T10:00:00Z",
        "effective_risk": risk_level.value,
        "risk_score": risk_score,
    }


class TestRecommender:
    def test_priority_1_fewest_severe_miles_dominates_time(self):
        # Route A: 0 Severe miles, 12 hours travel time
        # Route B: 25 Severe miles, 8 hours travel time (faster, but has severe miles)
        cps_a = [
            make_checkpoint(0, 0.0, 50.0, RiskLevel.LOW, 1.0),
            make_checkpoint(1, 50.0, 50.0, RiskLevel.MODERATE, 2.0),
        ]
        route_a = calculate_route_metrics("route_a", "Route A", 100.0, 12.0, cps_a, {})

        cps_b = [
            make_checkpoint(0, 0.0, 75.0, RiskLevel.LOW, 1.0),
            make_checkpoint(1, 75.0, 25.0, RiskLevel.SEVERE, 4.0),
        ]
        route_b = calculate_route_metrics("route_b", "Route B", 100.0, 8.0, cps_b, {})

        ranked = rank_and_recommend_routes([route_b, route_a])
        # Route A must win because it has 0 Severe miles
        assert ranked[0]["route_id"] == "route_a"
        assert ranked[0]["is_recommended"] is True
        assert ranked[0]["rank"] == 1
        assert ranked[1]["route_id"] == "route_b"
        assert ranked[1]["rank"] == 2

    def test_priority_2_fewest_high_miles_breaks_tie(self):
        # Both have 0 Severe miles
        # Route A has 10 High miles, Route B has 30 High miles
        cps_a = [
            make_checkpoint(0, 0.0, 90.0, RiskLevel.LOW, 1.0),
            make_checkpoint(1, 90.0, 10.0, RiskLevel.HIGH, 3.0),
        ]
        route_a = calculate_route_metrics("route_a", "Route A", 100.0, 10.0, cps_a, {})

        cps_b = [
            make_checkpoint(0, 0.0, 70.0, RiskLevel.LOW, 1.0),
            make_checkpoint(1, 70.0, 30.0, RiskLevel.HIGH, 3.0),
        ]
        route_b = calculate_route_metrics("route_b", "Route B", 100.0, 9.5, cps_b, {})

        ranked = rank_and_recommend_routes([route_b, route_a])
        assert ranked[0]["route_id"] == "route_a"

    def test_priority_3_lowest_average_risk_breaks_tie(self):
        # Both have 0 Severe, 0 High miles
        # Route A has mostly Low (avg risk 1.2), Route B has mostly Moderate (avg risk 1.8)
        cps_a = [
            make_checkpoint(0, 0.0, 80.0, RiskLevel.LOW, 1.0),
            make_checkpoint(1, 80.0, 20.0, RiskLevel.MODERATE, 2.0),
        ]
        route_a = calculate_route_metrics("route_a", "Route A", 100.0, 10.0, cps_a, {})

        cps_b = [
            make_checkpoint(0, 0.0, 20.0, RiskLevel.LOW, 1.0),
            make_checkpoint(1, 20.0, 80.0, RiskLevel.MODERATE, 2.0),
        ]
        route_b = calculate_route_metrics("route_b", "Route B", 100.0, 9.8, cps_b, {})

        ranked = rank_and_recommend_routes([route_b, route_a])
        assert ranked[0]["route_id"] == "route_a"
        assert ranked[0]["average_risk_score"] < ranked[1]["average_risk_score"]

    def test_priority_4_shortest_time_breaks_tie(self):
        # Both identical in risk profiles, Route A is 8 hours, Route B is 10 hours
        cps_a = [make_checkpoint(0, 0.0, 100.0, RiskLevel.LOW, 1.0)]
        route_a = calculate_route_metrics("route_a", "Route A", 100.0, 8.0, cps_a, {})

        cps_b = [make_checkpoint(0, 0.0, 100.0, RiskLevel.LOW, 1.0)]
        route_b = calculate_route_metrics("route_b", "Route B", 100.0, 10.0, cps_b, {})

        ranked = rank_and_recommend_routes([route_b, route_a])
        assert ranked[0]["route_id"] == "route_a"

    def test_no_travel_route_is_flagged_and_deprioritized(self):
        # Route A has No Travel condition (15 miles of blizzard)
        # Route B is safe with some High miles
        cps_a = [
            make_checkpoint(0, 0.0, 85.0, RiskLevel.LOW, 1.0),
            make_checkpoint(1, 85.0, 15.0, RiskLevel.NO_TRAVEL, 5.0),
        ]
        route_a = calculate_route_metrics("route_a", "Route A", 100.0, 7.0, cps_a, {})
        assert route_a["has_no_travel"] is True

        cps_b = [
            make_checkpoint(0, 0.0, 80.0, RiskLevel.LOW, 1.0),
            make_checkpoint(1, 80.0, 20.0, RiskLevel.HIGH, 3.0),
        ]
        route_b = calculate_route_metrics("route_b", "Route B", 100.0, 9.0, cps_b, {})
        assert route_b["has_no_travel"] is False

        ranked = rank_and_recommend_routes([route_a, route_b])
        assert ranked[0]["route_id"] == "route_b"
        assert ranked[1]["route_id"] == "route_a"
        assert ranked[1]["has_no_travel"] is True


class TestUnknownWeatherRiskPolicy:
    def test_all_checkpoints_unknown(self):
        cps = [
            make_checkpoint(0, 0.0, 25.0, RiskLevel.UNKNOWN, None),
            make_checkpoint(1, 25.0, 25.0, RiskLevel.UNKNOWN, None),
        ]
        route = calculate_route_metrics("r_unk", "Unknown Route", 50.0, 1.0, cps, {})
        assert route["average_risk_score"] is None
        assert route["risk_mileage"]["unknown_miles"] == 50.0
        assert route["risk_mileage"]["evaluated_miles"] == 0.0
        assert route["weather_coverage_pct"] == 0.0
        assert route["is_weather_complete"] is False
        assert route["overall_classification"] == "Unknown"
        assert route["risk_mileage"]["total_accounted_miles"] == 50.0

    def test_mixed_known_and_unknown_segments(self):
        cps = [
            make_checkpoint(0, 0.0, 30.0, RiskLevel.LOW, 1.0),
            make_checkpoint(1, 30.0, 20.0, RiskLevel.UNKNOWN, None),
        ]
        route = calculate_route_metrics("r_mixed", "Mixed Route", 50.0, 1.0, cps, {})
        assert route["risk_mileage"]["low_miles"] == 30.0
        assert route["risk_mileage"]["unknown_miles"] == 20.0
        assert route["risk_mileage"]["evaluated_miles"] == 30.0
        assert route["weather_coverage_pct"] == 60.0
        assert route["average_risk_score"] == 1.00
        assert route["overall_classification"] == "Incomplete Coverage"
        assert route["risk_mileage"]["total_accounted_miles"] == 50.0

    def test_zero_evaluated_mileage_never_displays_zero_risk(self):
        cps = [
            make_checkpoint(0, 0.0, 100.0, RiskLevel.UNKNOWN, None),
        ]
        route = calculate_route_metrics("r_zero", "Zero Evaluated", 100.0, 2.0, cps, {})
        assert route["average_risk_score"] is None
        assert route["average_risk_score"] != 0.0

    def test_different_weather_coverage_among_alternatives(self):
        # Route A: Fully monitored 100% coverage, 0 Severe, 0 High, avg risk 1.2
        cps_a = [
            make_checkpoint(0, 0.0, 80.0, RiskLevel.LOW, 1.0),
            make_checkpoint(1, 80.0, 20.0, RiskLevel.MODERATE, 2.0),
        ]
        route_a = calculate_route_metrics("route_a", "Route A (Monitored)", 100.0, 2.0, cps_a, {})

        # Route B: 100% unmonitored / missing forecasts, 0 Severe, 0 High, avg risk None
        cps_b = [
            make_checkpoint(0, 0.0, 100.0, RiskLevel.UNKNOWN, None),
        ]
        route_b = calculate_route_metrics("route_b", "Route B (Unmonitored)", 100.0, 1.8, cps_b, {})

        # Route A must win because missing weather is not treated as favorable
        ranked = rank_and_recommend_routes([route_b, route_a])
        assert ranked[0]["route_id"] == "route_a"
        assert ranked[0]["is_recommended"] is True
        assert ranked[1]["route_id"] == "route_b"
        assert ranked[1]["rank"] == 2

    def test_no_travel_miles_versus_unknown_miles(self):
        # Route A has lethal No Travel conditions
        cps_a = [
            make_checkpoint(0, 0.0, 50.0, RiskLevel.LOW, 1.0),
            make_checkpoint(1, 50.0, 50.0, RiskLevel.NO_TRAVEL, 5.0),
        ]
        route_a = calculate_route_metrics("route_a", "Route A (No Travel)", 100.0, 2.0, cps_a, {})
        assert route_a["has_no_travel"] is True

        # Route B has unknown miles (unmonitored), but 0 No Travel
        cps_b = [
            make_checkpoint(0, 0.0, 100.0, RiskLevel.UNKNOWN, None),
        ]
        route_b = calculate_route_metrics("route_b", "Route B (Unknown)", 100.0, 2.5, cps_b, {})
        assert route_b["has_no_travel"] is False

        # Route B must rank ahead of lethal No Travel Route A
        ranked = rank_and_recommend_routes([route_a, route_b])
        assert ranked[0]["route_id"] == "route_b"
        assert ranked[1]["route_id"] == "route_a"

    def test_distance_reconciliation_with_unknown_miles(self):
        # Route with 10 mi Low, 15 mi Mod, 20 mi High, 5 mi Severe, 10 mi No Travel, 40 mi Unknown = 100 mi
        cps = [
            make_checkpoint(0, 0.0, 10.0, RiskLevel.LOW, 1.0),
            make_checkpoint(1, 10.0, 15.0, RiskLevel.MODERATE, 2.0),
            make_checkpoint(2, 25.0, 20.0, RiskLevel.HIGH, 3.0),
            make_checkpoint(3, 45.0, 5.0, RiskLevel.SEVERE, 4.0),
            make_checkpoint(4, 50.0, 10.0, RiskLevel.NO_TRAVEL, 5.0),
            make_checkpoint(5, 60.0, 40.0, RiskLevel.UNKNOWN, None),
        ]
        route = calculate_route_metrics("r_recon", "Reconciliation Route", 100.0, 2.0, cps, {})
        m = route["risk_mileage"]
        assert m["low_miles"] == 10.0
        assert m["moderate_miles"] == 15.0
        assert m["high_miles"] == 20.0
        assert m["severe_miles"] == 5.0
        assert m["no_travel_miles"] == 10.0
        assert m["unknown_miles"] == 40.0
        assert m["evaluated_miles"] == 60.0
        assert m["total_accounted_miles"] == 100.0

    def test_recommendation_wording_when_coverage_is_incomplete(self):
        # Incomplete coverage route (e.g. 70% coverage)
        cps = [
            make_checkpoint(0, 0.0, 70.0, RiskLevel.LOW, 1.0),
            make_checkpoint(1, 70.0, 30.0, RiskLevel.UNKNOWN, None),
        ]
        route = calculate_route_metrics("r_inc", "Incomplete Route", 100.0, 2.0, cps, {})
        ranked = rank_and_recommend_routes([route])
        rec = ranked[0]
        reasons_text = " ".join(rec["recommendation_reasons"])
        assert "Safest route" not in rec["recommendation_reasons"][1]
        assert "Lowest risk among evaluated segments" in reasons_text
        assert "Incomplete weather coverage" in reasons_text
        assert "safety cannot be fully evaluated" in reasons_text
