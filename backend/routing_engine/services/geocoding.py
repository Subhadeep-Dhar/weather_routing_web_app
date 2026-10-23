"""
Geocoding service using Photon (Komoot OSM) with Nominatim fallback.
Completely free, no API key required, with caching and polite request handling.
"""

import requests
from typing import List, Dict, Any
from django.core.cache import cache

USER_AGENT = "SpotterWeatherAwareTruckRouter/1.0 (dev@spottertrucking.local)"
GEOCODE_CACHE_TIMEOUT = 3600 * 24  # 24 hours


def geocode_address(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Geocodes an address string to candidate coordinates.
    Returns:
        [
            {"name": "Chicago, Illinois, United States", "lat": 41.87556, "lon": -87.62442},
            ...
        ]
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    import re
    safe_q = re.sub(r'[^a-zA-Z0-9_]', '_', clean_query.lower())
    cache_key = f"geocode_{safe_q}_{limit}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    results = []

    # 1. Primary: Photon (OSM-based by Komoot, high performance, generous fair-use)
    try:
        resp = requests.get(
            "https://photon.komoot.io/api/",
            params={"q": clean_query, "limit": limit},
            headers={"User-Agent": USER_AGENT},
            timeout=5.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            features = data.get("features", [])
            for feat in features:
                props = feat.get("properties", {})
                coords = feat.get("geometry", {}).get("coordinates", [])
                if len(coords) >= 2:
                    name_parts = [
                        props.get("name"),
                        props.get("city"),
                        props.get("state"),
                        props.get("country"),
                    ]
                    display_name = ", ".join([p for p in name_parts if p])
                    if not display_name:
                        display_name = props.get("name", clean_query)
                    results.append({
                        "name": display_name,
                        "lat": coords[1],
                        "lon": coords[0],
                    })
    except Exception:
        results = []

    # 2. Fallback: Nominatim (OpenStreetMap) if Photon yielded no results
    if not results:
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": clean_query, "format": "json", "limit": limit},
                headers={"User-Agent": USER_AGENT},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data:
                    results.append({
                        "name": item.get("display_name", clean_query),
                        "lat": float(item.get("lat")),
                        "lon": float(item.get("lon")),
                    })
        except Exception:
            pass

    if results:
        cache.set(cache_key, results, GEOCODE_CACHE_TIMEOUT)

    return results
