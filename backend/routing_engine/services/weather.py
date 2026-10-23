"""
Weather service integrating Open-Meteo API for real checkpoint arrival weather and 0-48h corridor timeline.
Uses batch multi-coordinate queries and aligns each checkpoint's estimated arrival time with hourly forecasts.
"""

import requests
from datetime import datetime, timezone
from typing import List, Dict, Any
from django.core.cache import cache
from .risk_engine import evaluate_checkpoint_risk

OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "SpotterWeatherRoutingApp/1.0"
WEATHER_CACHE_TIMEOUT = 900  # 15 minutes


def _parse_iso_to_dt(iso_str: str) -> datetime:
    """Parses an ISO 8601 string to a UTC datetime object."""
    try:
        # Handle 'Z' or offset
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        return datetime.fromisoformat(iso_str).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _find_nearest_hour_index(target_dt: datetime, forecast_times: List[str]) -> int:
    """Finds the index of the forecast time closest to the target datetime."""
    if not forecast_times:
        return 0

    best_idx = 0
    min_diff = float("inf")

    target_ts = target_dt.timestamp()

    for idx, t_str in enumerate(forecast_times):
        # Open-Meteo times are formatted 'YYYY-MM-DDTHH:00'
        try:
            t_dt = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
            diff = abs(target_ts - t_dt.timestamp())
            if diff < min_diff:
                min_diff = diff
                best_idx = idx
        except Exception:
            continue

    return best_idx


def enrich_checkpoints_with_weather(
    checkpoints: List[Dict[str, Any]],
    cargo_weight_lbs: float,
    departure_time_iso: str,
) -> List[Dict[str, Any]]:
    """
    Batches checkpoint coordinates to Open-Meteo, aligns ETAs, and attaches
    weather data, risk evaluations, and 0-48h forecast timelines.
    """
    if not checkpoints:
        return []

    # Prepare comma-separated latitude and longitude lists for Open-Meteo batch request
    lats_str = ",".join(str(cp["lat"]) for cp in checkpoints)
    lons_str = ",".join(str(cp["lon"]) for cp in checkpoints)

    cache_key = f"weather_batch_{len(checkpoints)}_{checkpoints[0]['lat']}_{checkpoints[-1]['lat']}_{cargo_weight_lbs}"
    cached_weather = cache.get(cache_key)

    raw_weather_list = cached_weather
    if not raw_weather_list:
        params = {
            "latitude": lats_str,
            "longitude": lons_str,
            "hourly": "temperature_2m,precipitation,snowfall,wind_speed_10m",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "temperature_unit": "fahrenheit",
            "forecast_days": 3,
        }
        try:
            resp = requests.get(
                OPEN_METEO_BASE_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=12.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    raw_weather_list = data
                elif isinstance(data, dict):
                    raw_weather_list = [data]
                if raw_weather_list:
                    cache.set(cache_key, raw_weather_list, WEATHER_CACHE_TIMEOUT)
        except Exception:
            raw_weather_list = []

    dep_dt = _parse_iso_to_dt(departure_time_iso)

    enriched = []
    for idx, cp in enumerate(checkpoints):
        # Match weather result for this checkpoint
        loc_weather = (
            raw_weather_list[idx]
            if raw_weather_list and idx < len(raw_weather_list)
            else {}
        )
        hourly = loc_weather.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        precips = hourly.get("precipitation", [])
        snows = hourly.get("snowfall", [])
        winds = hourly.get("wind_speed_10m", [])

        cp_eta_dt = _parse_iso_to_dt(cp.get("eta", departure_time_iso))
        nearest_idx = _find_nearest_hour_index(cp_eta_dt, times) if times else 0

        wind_val = float(winds[nearest_idx]) if winds and nearest_idx < len(winds) else 5.0
        rain_val = float(precips[nearest_idx]) if precips and nearest_idx < len(precips) else 0.0
        snow_val = float(snows[nearest_idx]) if snows and nearest_idx < len(snows) else 0.0
        temp_val = float(temps[nearest_idx]) if temps and nearest_idx < len(temps) else 55.0

        risk_eval = evaluate_checkpoint_risk(wind_val, rain_val, snow_val, cargo_weight_lbs)

        # Build 0-48h timeline for this checkpoint (enabling instant slider scrubbing on frontend)
        timeline = []
        dep_hour_idx = _find_nearest_hour_index(dep_dt, times) if times else 0
        for h in range(49):  # 0 to 48 hours
            f_idx = dep_hour_idx + h
            if times and f_idx < len(times):
                h_wind = float(winds[f_idx]) if winds and f_idx < len(winds) else 5.0
                h_rain = float(precips[f_idx]) if precips and f_idx < len(precips) else 0.0
                h_snow = float(snows[f_idx]) if snows and f_idx < len(snows) else 0.0
                h_temp = float(temps[f_idx]) if temps and f_idx < len(temps) else 55.0
                h_risk = evaluate_checkpoint_risk(h_wind, h_rain, h_snow, cargo_weight_lbs)

                timeline.append({
                    "hour_offset": h,
                    "timestamp": times[f_idx],
                    "wind_speed_mph": round(h_wind, 1),
                    "rain_intensity_in_hr": round(h_rain, 2),
                    "snow_intensity_in_hr": round(h_snow, 2),
                    "temperature_f": round(h_temp, 1),
                    "effective_risk": h_risk["effective_risk"],
                    "risk_score": h_risk["risk_score"],
                })

        cp_copy = dict(cp)
        cp_copy["weather"] = {
            "wind_speed_mph": round(wind_val, 1),
            "rain_intensity_in_hr": round(rain_val, 2),
            "snow_intensity_in_hr": round(snow_val, 2),
            "temperature_f": round(temp_val, 1),
            "forecast_timestamp": times[nearest_idx] if times and nearest_idx < len(times) else cp["eta"],
        }
        cp_copy["hazard_classifications"] = {
            "wind": risk_eval["raw_wind_risk"],
            "effective_wind": risk_eval["effective_wind_risk"],
            "rain": risk_eval["rain_risk"],
            "snow": risk_eval["snow_risk"],
        }
        cp_copy["cargo_override_applied"] = risk_eval["cargo_override_reason"]
        cp_copy["effective_risk"] = risk_eval["effective_risk"]
        cp_copy["risk_score"] = risk_eval["risk_score"]
        cp_copy["timeline_48h"] = timeline

        enriched.append(cp_copy)

    return enriched
