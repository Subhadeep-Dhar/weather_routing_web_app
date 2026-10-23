"""
Geospatial checkpoint generation and segment distance attribution.
Samples checkpoints along actual route geometry at configurable intervals (10, 25, 50 miles)
and computes arrival times (ETAs) and reconciled segment distances.
"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple


# Earth mean radius in miles (WGS-84 spherical approximation)
EARTH_RADIUS_MILES = 3958.7613


def haversine_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two coordinates in miles."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_MILES * c


def compute_cumulative_distances(coordinates: List[List[float]]) -> Tuple[List[float], float]:
    """
    Computes cumulative distance in miles along a polyline.
    Coordinates format: [[lon, lat], [lon, lat], ...] (GeoJSON standard)
    Returns:
        (cumulative_distances_list, total_distance_miles)
    """
    if not coordinates or len(coordinates) < 2:
        return [0.0], 0.0

    cumulative = [0.0]
    total = 0.0
    for i in range(1, len(coordinates)):
        lon1, lat1 = coordinates[i - 1]
        lon2, lat2 = coordinates[i]
        d = haversine_distance_miles(lat1, lon1, lat2, lon2)
        total += d
        cumulative.append(total)

    return cumulative, total


def interpolate_coordinate(
    p1: List[float], p2: List[float], ratio: float
) -> Tuple[float, float]:
    """Interpolates (lat, lon) between two [lon, lat] coordinates."""
    lon1, lat1 = p1
    lon2, lat2 = p2
    lat = lat1 + ratio * (lat2 - lat1)
    lon = lon1 + ratio * (lon2 - lon1)
    return lat, lon


def find_point_at_distance(
    coordinates: List[List[float]],
    cumulative_distances: List[float],
    target_distance: float,
) -> Tuple[float, float]:
    """
    Finds the exact coordinate (lat, lon) at target_distance miles along the polyline.
    """
    if target_distance <= 0:
        return coordinates[0][1], coordinates[0][0]
    if target_distance >= cumulative_distances[-1]:
        return coordinates[-1][1], coordinates[-1][0]

    for i in range(1, len(cumulative_distances)):
        if cumulative_distances[i] >= target_distance:
            d_prev = cumulative_distances[i - 1]
            d_curr = cumulative_distances[i]
            segment_len = d_curr - d_prev
            ratio = (target_distance - d_prev) / segment_len if segment_len > 0 else 0.0
            return interpolate_coordinate(coordinates[i - 1], coordinates[i], ratio)

    return coordinates[-1][1], coordinates[-1][0]


def calculate_segment_distances(checkpoint_distances: List[float], total_route_distance: float) -> List[float]:
    """
    Assigns each checkpoint a representative segment distance using Voronoi/midpoint boundaries.
    Guarantees that sum(segment_distances) == total_route_distance within 1e-4 tolerance.
    """
    n = len(checkpoint_distances)
    if n == 0:
        return []
    if n == 1:
        return [round(total_route_distance, 4)]

    # Calculate midpoints between consecutive checkpoints
    midpoints = []
    for i in range(n - 1):
        midpoints.append((checkpoint_distances[i] + checkpoint_distances[i + 1]) / 2.0)

    segment_distances = []
    # First checkpoint covers [0, midpoint[0]]
    segment_distances.append(midpoints[0])

    # Middle checkpoints cover [midpoint[i-1], midpoint[i]]
    for i in range(1, n - 1):
        segment_distances.append(midpoints[i] - midpoints[i - 1])

    # Last checkpoint covers [midpoint[-1], total_route_distance]
    segment_distances.append(total_route_distance - midpoints[-1])

    # Reconcile rounding discrepancy to the last segment
    accounted_sum = sum(segment_distances)
    diff = total_route_distance - accounted_sum
    segment_distances[-1] += diff

    return [round(s, 4) for s in segment_distances]


def generate_route_checkpoints(
    coordinates: List[List[float]],
    total_route_distance_miles: float,
    total_duration_seconds: float,
    departure_time: datetime,
    interval_miles: float = 25.0,
) -> List[Dict[str, Any]]:
    """
    Generates sampled checkpoints along route polyline.
    Returns structured checkpoint objects with distance, lat, lon, ETA, and segment_distance_miles.
    """
    if interval_miles not in [10.0, 25.0, 50.0]:
        interval_miles = 25.0

    cumulative_distances, poly_total = compute_cumulative_distances(coordinates)
    effective_total = total_route_distance_miles if total_route_distance_miles > 0 else poly_total

    # Determine sample distances: 0, interval, 2*interval, ... up to effective_total
    sample_distances = [0.0]
    curr_d = interval_miles
    while curr_d < effective_total - (interval_miles * 0.25):
        sample_distances.append(round(curr_d, 2))
        curr_d += interval_miles

    # Always include the destination checkpoint
    if sample_distances[-1] != effective_total:
        sample_distances.append(round(effective_total, 2))

    segment_distances = calculate_segment_distances(sample_distances, effective_total)

    checkpoints = []
    for idx, d in enumerate(sample_distances):
        lat, lon = find_point_at_distance(coordinates, cumulative_distances, d)

        # ETA calculation: proportional to distance along route
        fraction = d / effective_total if effective_total > 0 else 0.0
        elapsed_seconds = fraction * total_duration_seconds
        eta = departure_time + timedelta(seconds=elapsed_seconds)

        checkpoints.append({
            "index": idx,
            "distance_from_origin_miles": d,
            "segment_distance_miles": segment_distances[idx],
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "eta": eta.isoformat(),
            "elapsed_hours": round(elapsed_seconds / 3600.0, 2),
        })

    return checkpoints
