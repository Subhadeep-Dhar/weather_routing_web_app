"""
Heuristic Commercial-Truck Transit Time (ETA) Model.

The public OSRM driving profile assumes an unrestricted passenger car travelling on
uncongested, flat roads according to default OpenStreetMap highway speed limits
(e.g. 85 km/h on trunk roads, even in narrow mountain passes).

This service applies transparent, documented transport-engineering heuristic adjustments
on top of OSRM route geometries:
1. Terrain and Curvature Detection:
   - Route Sinuosity (ratio of route distance to Great-Circle straight-line distance).
   - Elevation Change (derived from Open-Meteo Free Elevation API or terrain heuristics).
   - Classifies corridor into: 'mountain', 'ghat_corridor', 'rolling', or 'flat'.

2. Heavy Vehicle Heuristic Speed Restrictions & Capabilities:
   - Mountain corridors (e.g. Siliguri-Gangtok): Heavy commercial trucks are
     heuristically constrained to 20-32 km/h (12-20 mph) due to hairpin turns, single-lane
     bottlenecks, grade ascents, and mandatory low-gear engine braking on steep descents.
   - Ghat corridors: Distinguishes concentrated switchbacks (24 km/h) from connecting highways.
   - Rolling corridors: Speed governed to 50-65 km/h (31-40 mph).
   - Flat corridors: Fleet speed-limiter cap of 88-92 km/h (55-57 mph).

3. Cargo Weight Heuristic Assumptions:
   - Note: The system does not know specific vehicle tare weight, engine brake horsepower,
     torque curves, or drivetrain gearing. Cargo weight thresholds (>40k lbs, 30-40k lbs)
     are heuristic operational assumptions rather than vehicle-specific measurements.

4. Operational & Rest Buffers:
   - Mountain passes: Heuristic buffer of 20 min per 100 km for brake cooling and checkpoint queues.
   - Inter-city / Flat corridors: Standard commercial safety rest buffers (15 min per 4-4.5 hours).

5. Metric Transparency:
   - Keeps raw OSRM passenger car duration separately for diagnostic comparison.
"""

import math
import logging
import requests
from typing import Dict, Any, Tuple, Optional, List
from django.core.cache import cache

logger = logging.getLogger(__name__)

ELEVATION_CACHE_TIMEOUT = 3600 * 24 * 30  # 30 days (terrain is immutable)
USER_AGENT = "SpotterTruckETAModel/1.0"


def haversine_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes the great-circle distance between two GPS points in miles."""
    r_miles = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r_miles * c


def fetch_coordinate_elevations(
    coords: List[Tuple[float, float]]
) -> List[Optional[float]]:
    """
    Fetches elevations in meters for a list of (lat, lon) coordinates using
    Open-Meteo's free public Elevation API. Caches results permanently.
    """
    if not coords:
        return []

    elevations: List[Optional[float]] = [None] * len(coords)
    missing_indices = []
    missing_lats = []
    missing_lons = []

    for idx, (lat, lon) in enumerate(coords):
        cache_key = f"elev_{lat:.4f}_{lon:.4f}"
        cached_val = cache.get(cache_key)
        if cached_val is not None:
            elevations[idx] = cached_val
        else:
            missing_indices.append(idx)
            missing_lats.append(f"{lat:.4f}")
            missing_lons.append(f"{lon:.4f}")

    if missing_indices:
        try:
            url = f"https://api.open-meteo.com/v1/elevation?latitude={','.join(missing_lats)}&longitude={','.join(missing_lons)}"
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                api_elevs = data.get("elevation", [])
                for i, orig_idx in enumerate(missing_indices):
                    if i < len(api_elevs) and api_elevs[i] is not None:
                        val = float(api_elevs[i])
                        elevations[orig_idx] = val
                        cache.set(f"elev_{missing_lats[i]}_{missing_lons[i]}", val, ELEVATION_CACHE_TIMEOUT)
        except Exception as e:
            logger.warning("Could not fetch elevations from Open-Meteo: %s", e)

    return elevations


def calculate_defensible_truck_eta(
    distance_miles: float,
    raw_duration_seconds: float,
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    cargo_weight_lbs: float,
    checkpoint_coords: Optional[List[Tuple[float, float]]] = None,
) -> Dict[str, Any]:
    """
    Computes a realistic, defensible commercial truck transit time and terrain profile.
    """
    dist_km = distance_miles * 1.609344
    raw_duration_hours = max(0.01, raw_duration_seconds / 3600.0)
    implied_car_speed_kmh = dist_km / raw_duration_hours if raw_duration_hours > 0 else 60.0

    # 1. Calculate Great-Circle Straight-Line Distance & Sinuosity
    straight_line_miles = haversine_distance_miles(origin_lat, origin_lon, dest_lat, dest_lon)
    sinuosity = (
        round(distance_miles / straight_line_miles, 2)
        if straight_line_miles > 1.0
        else 1.0
    )

    # 2. Fetch Elevations for Terrain Analysis
    elevation_points = [(origin_lat, origin_lon), (dest_lat, dest_lon)]
    if checkpoint_coords and len(checkpoint_coords) > 2:
        # Sample midpoints for comprehensive elevation profiling
        elevation_points.extend(checkpoint_coords[1:-1])

    elev_results = fetch_coordinate_elevations(elevation_points)
    elev_orig = elev_results[0] if len(elev_results) > 0 else None
    elev_dest = elev_results[1] if len(elev_results) > 1 else None

    # Calculate net and cumulative elevation gain if available
    elev_delta = 0.0
    if elev_orig is not None and elev_dest is not None:
        elev_delta = abs(elev_dest - elev_orig)

    # Check max elevation along the route
    max_elev = max([e for e in elev_results if e is not None], default=0.0)
    min_elev = min([e for e in elev_results if e is not None], default=0.0)
    elev_span = max_elev - min_elev

    # 3. Classify Corridor Terrain
    # Mountain criteria:
    # - Net elevation change >= 500m OR
    # - Elevation span >= 500m along route OR
    # - High sinuosity (>= 1.40) with significant elevation (span >= 300m)
    is_mountain_pass = (elev_span >= 500.0) or (elev_delta >= 500.0) or (sinuosity >= 1.40 and elev_span >= 300.0)
    is_rolling = (sinuosity >= 1.25) or (elev_span >= 200.0) or (elev_delta >= 200.0)

    assumptions = []

    if is_mountain_pass:
        # High sinuosity (>= 1.50) combined with high elevation span indicates continuous mountain winding throughout.
        # Moderate sinuosity (< 1.50) over longer distances indicates an inter-city highway crossing a mountain pass/ghat.
        if sinuosity >= 1.50 or dist_km <= 140.0:
            # Concentrated continuous mountain corridor (e.g. Siliguri -> Gangtok via NH10 or Kalimpong hills)
            terrain_type = "mountain"
            terrain_label = "Mountain / Himalayan Highway"
            disclaimer_type = "mountain"

            # Mountainous terrain: hairpins, single lanes, steep grades (5-10%)
            # Vehicle weight directly constrains ascent climbing speed and descent engine-braking safety
            if cargo_weight_lbs > 40000.0:
                target_speed_kmh = 24.0  # ~15 mph (heavy crawl)
                assumptions.append(f"Heavy cargo load ({cargo_weight_lbs:,.0f} lb > 40k lb) on mountain grade ({round(elev_span)}m rise): heuristic climb speed governed to ~24 km/h (15 mph) for engine torque and thermal brake safety.")
            elif cargo_weight_lbs > 30000.0:
                target_speed_kmh = 28.0  # ~17.5 mph
                assumptions.append(f"Standard commercial load ({cargo_weight_lbs:,.0f} lb): heuristic hill ascent speed governed to ~28 km/h (17.5 mph).")
            else:
                target_speed_kmh = 32.0  # ~20 mph
                assumptions.append(f"Light/empty commercial load ({cargo_weight_lbs:,.0f} lb): heuristic mountain switchback speed governed to ~32 km/h (20 mph).")

            assumptions.append(f"High corridor sinuosity ({sinuosity:.2f}x) and {round(elev_span)}m elevation span: OSRM car baseline ({implied_car_speed_kmh:.1f} km/h) adjusted for heavy vehicle cornering radius.")

            # Driving time
            driving_hours = dist_km / target_speed_kmh

            # Operational buffers in mountain corridors: 20 min per 100 km (brake cool-down, checkposts, narrow bridge passes)
            buffer_hours = (dist_km / 100.0) * (20.0 / 60.0)
            assumptions.append(f"Mountain pass operational buffer: +{round(buffer_hours * 60)} min for brake cooling, toll/state checkposts, and narrow bridge queues.")

            truck_duration_hours = driving_hours + buffer_hours

        else:
            # Inter-city corridor crossing a mountain pass or ghat section (e.g. Bengaluru -> Mangaluru via Western Ghats)
            terrain_type = "ghat_corridor"
            terrain_label = "Inter-City Ghat Corridor"
            disclaimer_type = "ghat"

            # Model ghat segment vs plateau/coastal highway
            ghat_km = min(75.0, dist_km * 0.22)
            highway_km = dist_km - ghat_km

            ghat_speed_kmh = 24.0 if cargo_weight_lbs > 40000.0 else 28.0
            hwy_speed_cap = 65.0 if cargo_weight_lbs > 40000.0 else 72.0
            hwy_speed_kmh = min(implied_car_speed_kmh * 0.85, hwy_speed_cap)

            ghat_hours = ghat_km / ghat_speed_kmh
            hwy_hours = highway_km / hwy_speed_kmh
            buffer_hours = (dist_km / 150.0) * (15.0 / 60.0)

            assumptions.append(f"Ghat pass section ({round(ghat_km)} km): heavy vehicle speed restricted to {ghat_speed_kmh:.0f} km/h through switchbacks.")
            assumptions.append(f"Highway section ({round(highway_km)} km): truck speed governed to {round(hwy_speed_kmh)} km/h.")
            assumptions.append(f"Commercial operational buffer: +{round(buffer_hours * 60)} min for mandatory rest intervals and toll checkpoints.")

            truck_duration_hours = ghat_hours + hwy_hours + buffer_hours

    elif is_rolling:
        # Rolling corridor: moderate curves and grades
        terrain_type = "rolling"
        terrain_label = "Rolling / Winding Corridor"
        disclaimer_type = "rolling"

        speed_cap = 60.0 if cargo_weight_lbs > 40000.0 else 68.0
        truck_speed_kmh = min(implied_car_speed_kmh * 0.80, speed_cap)
        assumptions.append(f"Rolling corridor ({sinuosity:.2f}x curvature): truck cruising speed governed to {round(truck_speed_kmh)} km/h based on grade handling.")

        driving_hours = dist_km / truck_speed_kmh
        buffer_hours = (driving_hours / 4.0) * (15.0 / 60.0)  # 15 min per 4h
        truck_duration_hours = driving_hours + buffer_hours

    else:
        # Flat Highway / Interstate Corridor
        terrain_type = "flat"
        terrain_label = "Standard Highway / Interstate"
        disclaimer_type = "highway"

        # Fleet speed limiters typically cap commercial trucks at 88-100 km/h (55-62 mph)
        fleet_speed_cap_kmh = 92.0  # ~57 mph
        # Trucks accelerate slower and maintain longer following distance: 0.90x of unconstrained car speed
        target_speed_kmh = min(implied_car_speed_kmh * 0.90, fleet_speed_cap_kmh)

        if cargo_weight_lbs > 40000.0:
            # Minor inertia deceleration buffer
            target_speed_kmh *= 0.96

        assumptions.append(f"Standard highway corridor: heavy commercial vehicle speed governed at {round(target_speed_kmh)} km/h (fleet limiter & braking distance).")

        driving_hours = dist_km / target_speed_kmh
        buffer_hours = (driving_hours / 4.5) * (15.0 / 60.0)  # Standard safety rest interval
        truck_duration_hours = driving_hours + buffer_hours

    truck_duration_seconds = round(truck_duration_hours * 3600.0, 1)
    truck_duration_hours = round(truck_duration_hours, 2)

    return {
        "duration_raw_osrm_seconds": round(raw_duration_seconds, 1),
        "duration_raw_osrm_hours": round(raw_duration_hours, 2),
        "duration_truck_seconds": truck_duration_seconds,
        "duration_truck_hours": truck_duration_hours,
        "average_truck_speed_mph": round(distance_miles / truck_duration_hours, 1) if truck_duration_hours > 0 else 0.0,
        "average_truck_speed_kmh": round(dist_km / truck_duration_hours, 1) if truck_duration_hours > 0 else 0.0,
        "raw_implied_car_speed_kmh": round(implied_car_speed_kmh, 1),
        "terrain_classification": terrain_type,
        "terrain_label": terrain_label,
        "sinuosity": sinuosity,
        "elevation_delta_meters": round(elev_delta, 1),
        "elevation_span_meters": round(elev_span, 1),
        "elevation_origin_meters": round(elev_orig, 1) if elev_orig is not None else None,
        "elevation_dest_meters": round(elev_dest, 1) if elev_dest is not None else None,
        "model_assumptions": assumptions,
        "disclaimer_type": disclaimer_type,
    }
