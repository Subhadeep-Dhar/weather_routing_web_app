from datetime import datetime, timezone
from routing_engine.services.checkpoints import (
    haversine_distance_miles,
    compute_cumulative_distances,
    calculate_segment_distances,
    generate_route_checkpoints,
)


class TestCheckpoints:
    def test_haversine_distance(self):
        # NYC (40.7128, -74.0060) to Boston (42.3601, -71.0589) ~ 190-215 miles
        dist = haversine_distance_miles(40.7128, -74.0060, 42.3601, -71.0589)
        assert 185.0 < dist < 220.0

    def test_segment_distances_exact_reconciliation(self):
        # 4 checkpoints along a 75-mile route: 0, 25, 50, 75
        distances = [0.0, 25.0, 50.0, 75.0]
        segments = calculate_segment_distances(distances, 75.0)
        assert len(segments) == 4
        # Total reconciled sum should equal exactly 75.0
        assert round(sum(segments), 4) == 75.0

    def test_segment_distances_uneven_route(self):
        # Irregular checkpoints e.g. 0, 25, 50, 63.4
        distances = [0.0, 25.0, 50.0, 63.4]
        segments = calculate_segment_distances(distances, 63.4)
        assert len(segments) == 4
        assert round(sum(segments), 4) == 63.4

    def test_generate_route_checkpoints_multiple_intervals(self):
        # Synthetic 100-mile straight line route east to west
        coords = [
            [-80.0, 35.0],
            [-79.5, 35.0],
            [-79.0, 35.0],
            [-78.5, 35.0],
        ]
        dep_time = datetime(2026, 10, 24, 8, 0, 0, tzinfo=timezone.utc)
        total_dist = 85.0
        duration_s = 7200.0  # 2 hours

        # Interval 25 miles
        cps_25 = generate_route_checkpoints(coords, total_dist, duration_s, dep_time, interval_miles=25.0)
        assert len(cps_25) >= 4  # 0, 25, 50, 75, 85
        assert cps_25[0]["distance_from_origin_miles"] == 0.0
        assert cps_25[-1]["distance_from_origin_miles"] == total_dist

        # Check ETA progression
        for i in range(1, len(cps_25)):
            assert cps_25[i]["elapsed_hours"] > cps_25[i - 1]["elapsed_hours"]

        # Check segment distances sum to total distance
        total_accounted = sum(cp["segment_distance_miles"] for cp in cps_25)
        assert abs(total_accounted - total_dist) < 0.01

    def test_route_shorter_than_interval(self):
        # Route is only 8 miles, interval is 25 miles
        coords = [[-80.0, 35.0], [-79.9, 35.0]]
        dep_time = datetime(2026, 10, 24, 8, 0, 0, tzinfo=timezone.utc)
        cps = generate_route_checkpoints(coords, 8.0, 900.0, dep_time, interval_miles=25.0)
        # Should have origin and destination
        assert len(cps) == 2
        assert cps[0]["distance_from_origin_miles"] == 0.0
        assert cps[1]["distance_from_origin_miles"] == 8.0
        assert round(sum(cp["segment_distance_miles"] for cp in cps), 2) == 8.0
