"""
OSRM routing integration for real turn-by-turn driving routes, distances, durations, and geometries.
Ensures up to 3 distinct genuine route alternatives without fake data.
"""

import math
import requests
from typing import List, Dict, Any, Tuple
from django.core.cache import cache

OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/driving"
USER_AGENT = "SpotterWeatherRoutingApp/1.0"
ROUTING_CACHE_TIMEOUT = 3600 * 2  # 2 hours
METERS_TO_MILES = 1.0 / 1609.344


def _compute_corridor_waypoint(
    lat1: float, lon1: float, lat2: float, lon2: float, offset_ratio: float = 0.15, direction: int = 1
) -> Tuple[float, float]:
    """
    Computes a lateral corridor coordinate perpendicular to the origin-destination vector.
    Used to query a distinct highway corridor through OSRM when direct queries return fewer than 3 alternatives.
    """
    mid_lat = (lat1 + lat2) / 2.0
    mid_lon = (lon1 + lon2) / 2.0
    dx = lon2 - lon1
    dy = lat2 - lat1

    # Perpendicular vector (-dy, dx)
    p_lat = -dx * direction
    p_lon = dy * direction
    length = math.sqrt(p_lat**2 + p_lon**2)
    if length == 0:
        return mid_lat, mid_lon

    span = math.sqrt(dx**2 + dy**2)
    p_lat = (p_lat / length) * (span * offset_ratio)
    p_lon = (p_lon / length) * (span * offset_ratio)
    return round(mid_lat + p_lat, 6), round(mid_lon + p_lon, 6)


def _format_route_name(route_data: Dict[str, Any], index: int) -> str:
    """Extracts a recognizable road/highway name from OSRM legs, or returns fallback."""
    legs = route_data.get("legs", [])
    streets = []
    for leg in legs:
        steps = leg.get("steps", [])
        for step in steps:
            st = step.get("name")
            if st and st not in streets and not st.startswith("Route"):
                streets.append(st)
            if len(streets) >= 2:
                break
        if len(streets) >= 2:
            break

    if streets:
        return f"Via {' / '.join(streets[:2])}"
    return f"Route Option {index + 1}"


def fetch_route_options(
    origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float
) -> List[Dict[str, Any]]:
    """
    Fetches genuine route alternatives from OSRM.
    Returns:
        [
            {
                "route_id": "route_1",
                "name": "Via I-65 S",
                "distance_miles": 684.4,
                "duration_hours": 13.35,
                "duration_seconds": 48060.0,
                "geometry": {"type": "LineString", "coordinates": [[lon, lat], ...]}
            },
            ...
        ]
    """
    cache_key = f"osrm_routes_{origin_lat:.4f}_{origin_lon:.4f}_{dest_lat:.4f}_{dest_lon:.4f}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    routes_out = []

    # 1. Primary Direct OSRM query requesting alternatives
    url = f"{OSRM_BASE_URL}/{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson&alternatives=3"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            raw_routes = data.get("routes", [])
            for idx, r in enumerate(raw_routes):
                dist_mi = r.get("distance", 0.0) * METERS_TO_MILES
                dur_s = float(r.get("duration", 0.0))
                geom = r.get("geometry", {})
                name = _format_route_name(r, idx)
                routes_out.append({
                    "route_id": f"route_{idx + 1}",
                    "name": name,
                    "distance_miles": round(dist_mi, 2),
                    "duration_seconds": dur_s,
                    "duration_hours": round(dur_s / 3600.0, 2),
                    "geometry": geom,
                })
    except Exception as e:
        pass

    # 2. If direct OSRM returned fewer than 3 alternatives, find lateral highway corridor routes
    # via OSRM to supply genuine 3 distinct paths
    offset_configs = [
        (0.12, 1),   # Left lateral corridor
        (0.12, -1),  # Right lateral corridor
        (0.20, 1),   # Wider lateral corridor
        (0.20, -1),
    ]

    config_idx = 0
    while len(routes_out) < 3 and config_idx < len(offset_configs):
        ratio, direction = offset_configs[config_idx]
        config_idx += 1

        wp_lat, wp_lon = _compute_corridor_waypoint(
            origin_lat, origin_lon, dest_lat, dest_lon, offset_ratio=ratio, direction=direction
        )
        wp_url = f"{OSRM_BASE_URL}/{origin_lon},{origin_lat};{wp_lon},{wp_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson"
        try:
            wp_resp = requests.get(wp_url, headers={"User-Agent": USER_AGENT}, timeout=10.0)
            if wp_resp.status_code == 200:
                wp_data = wp_resp.json()
                wp_routes = wp_data.get("routes", [])
                if wp_routes:
                    r = wp_routes[0]
                    dist_mi = r.get("distance", 0.0) * METERS_TO_MILES
                    dur_s = float(r.get("duration", 0.0))
                    geom = r.get("geometry", {})

                    # Verify route is distinct (distance differs by at least 2% from existing routes)
                    is_distinct = True
                    for existing in routes_out:
                        diff_pct = abs(dist_mi - existing["distance_miles"]) / max(existing["distance_miles"], 1.0)
                        if diff_pct < 0.02:
                            is_distinct = False
                            break

                    if is_distinct:
                        next_idx = len(routes_out)
                        routes_out.append({
                            "route_id": f"route_{next_idx + 1}",
                            "name": _format_route_name(r, next_idx),
                            "distance_miles": round(dist_mi, 2),
                            "duration_seconds": dur_s,
                            "duration_hours": round(dur_s / 3600.0, 2),
                            "geometry": geom,
                        })
        except Exception:
            pass

    if routes_out:
        cache.set(cache_key, routes_out, ROUTING_CACHE_TIMEOUT)

    return routes_out
