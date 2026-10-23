from routing_engine.services.recommender import (
    calculate_route_metrics,
    rank_and_recommend_routes,
)
from routing_engine.services.risk_engine import RiskLevel


def make_checkpoint(idx: int, dist: float, seg_dist: float, risk_level: RiskLevel, risk_score: float):
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
