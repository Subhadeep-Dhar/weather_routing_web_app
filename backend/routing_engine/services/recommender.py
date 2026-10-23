"""
Route metrics calculation, distance-weighted risk averaging, and lexicographic recommendation engine.

Lexicographical priority order (from assessment specification):
1. Fewest Severe miles
2. Fewest High miles
3. Lowest average risk
4. Shortest travel times

Safety rule:
Routes with any No Travel conditions are flagged with has_no_travel=True. Safe routes (zero No Travel miles)
are strictly prioritized ahead of No Travel routes.
"""

from typing import List, Dict, Any, Tuple
from .risk_engine import RiskLevel, RISK_ORDINAL_MAP


def calculate_route_metrics(
    route_id: str,
    name: str,
    distance_miles: float,
    duration_hours: float,
    checkpoints: List[Dict[str, Any]],
    geometry: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Aggregates checkpoint risk classifications and segment distances into comprehensive route metrics.
    Ensures exact distance reconciliation.
    Evaluates average risk strictly over monitored segments (or returns None when unmonitored).
    """
    low_miles = 0.0
    mod_miles = 0.0
    high_miles = 0.0
    sev_miles = 0.0
    no_travel_miles = 0.0
    unknown_miles = 0.0

    weighted_risk_sum = 0.0
    total_segment_dist = 0.0

    has_no_travel = False
    highest_severity_encountered = RiskLevel.LOW

    for cp in checkpoints:
        seg_dist = cp.get("segment_distance_miles", 0.0)
        risk_str = cp.get("effective_risk", RiskLevel.LOW.value)
        risk_score = cp.get("risk_score")

        total_segment_dist += seg_dist

        if risk_str == RiskLevel.NO_TRAVEL.value:
            no_travel_miles += seg_dist
            has_no_travel = True
            highest_severity_encountered = RiskLevel.NO_TRAVEL
            if risk_score is not None:
                weighted_risk_sum += (seg_dist * risk_score)
        elif risk_str == RiskLevel.SEVERE.value:
            sev_miles += seg_dist
            if highest_severity_encountered != RiskLevel.NO_TRAVEL:
                highest_severity_encountered = RiskLevel.SEVERE
            if risk_score is not None:
                weighted_risk_sum += (seg_dist * risk_score)
        elif risk_str == RiskLevel.HIGH.value:
            high_miles += seg_dist
            if highest_severity_encountered in [RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.UNKNOWN]:
                highest_severity_encountered = RiskLevel.HIGH
            if risk_score is not None:
                weighted_risk_sum += (seg_dist * risk_score)
        elif risk_str == RiskLevel.MODERATE.value:
            mod_miles += seg_dist
            if highest_severity_encountered in [RiskLevel.LOW, RiskLevel.UNKNOWN]:
                highest_severity_encountered = RiskLevel.MODERATE
            if risk_score is not None:
                weighted_risk_sum += (seg_dist * risk_score)
        elif risk_str == RiskLevel.UNKNOWN.value:
            unknown_miles += seg_dist
            if highest_severity_encountered == RiskLevel.LOW:
                highest_severity_encountered = RiskLevel.UNKNOWN
            # Unknown miles do NOT add to weighted_risk_sum
        else:
            low_miles += seg_dist
            if risk_score is not None:
                weighted_risk_sum += (seg_dist * risk_score)

    evaluated_miles = round(low_miles + mod_miles + high_miles + sev_miles + no_travel_miles, 2)
    unknown_miles = round(unknown_miles, 2)
    total_accounted = round(evaluated_miles + unknown_miles, 2)

    weather_coverage_pct = (
        round((evaluated_miles / distance_miles) * 100.0, 1)
        if distance_miles > 0
        else 0.0
    )
    weather_coverage_pct = max(0.0, min(100.0, weather_coverage_pct))
    is_weather_complete = (unknown_miles == 0.0)

    # Numerical average risk calculated ONLY over evaluated segments.
    # If evaluated_miles == 0, average_risk_score MUST BE None (never 0.00!)
    if evaluated_miles > 0.0:
        avg_risk_score = round(weighted_risk_sum / evaluated_miles, 2)
    else:
        avg_risk_score = None

    # Overall classification determination
    if has_no_travel:
        overall_class = RiskLevel.NO_TRAVEL.value
    elif sev_miles > 0:
        overall_class = RiskLevel.SEVERE.value
    elif high_miles > 0:
        overall_class = RiskLevel.HIGH.value
    elif mod_miles > 0:
        overall_class = RiskLevel.MODERATE.value
    elif low_miles > 0 and is_weather_complete:
        overall_class = RiskLevel.LOW.value
    elif not is_weather_complete:
        if evaluated_miles == 0.0:
            overall_class = RiskLevel.UNKNOWN.value
        else:
            overall_class = "Incomplete Coverage"
    else:
        overall_class = RiskLevel.LOW.value

    return {
        "route_id": route_id,
        "name": name,
        "distance_miles": round(distance_miles, 1),
        "duration_hours": round(duration_hours, 2),
        "geometry": geometry,
        "checkpoints": checkpoints,
        "checkpoint_count": len(checkpoints),
        "has_no_travel": has_no_travel,
        "overall_classification": overall_class,
        "risk_mileage": {
            "low_miles": round(low_miles, 1),
            "moderate_miles": round(mod_miles, 1),
            "high_miles": round(high_miles, 1),
            "severe_miles": round(sev_miles, 1),
            "no_travel_miles": round(no_travel_miles, 1),
            "unknown_miles": round(unknown_miles, 1),
            "evaluated_miles": round(evaluated_miles, 1),
            "total_accounted_miles": total_accounted,
        },
        "weather_coverage_pct": weather_coverage_pct,
        "is_weather_complete": is_weather_complete,
        "average_risk_score": avg_risk_score,
        "recommendation_reasons": [],
        "is_recommended": False,
        "rank": 0,
    }


def rank_and_recommend_routes(routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ranks routes using strict lexicographical priority order with deterministic Unknown-data policy:
    1. Primary safety flag: has_no_travel (False < True)
    2. Fewest Severe miles (ascending)
    3. Fewest High-risk miles (ascending)
    4. Completeness of weather coverage (fewest unknown_miles, ascending: complete coverage preferred)
    5. Lowest average risk over evaluated segments (ascending: None ranked behind evaluated values)
    6. Shortest travel time (duration_hours)

    Returns routes sorted from best (rank 1) to worst, with recommendation explanations.
    """
    if not routes:
        return []

    def sort_key(r: Dict[str, Any]) -> Tuple[int, float, float, float, float, float]:
        # Flag 0 for safe (no travel == 0), 1 for unsafe
        safety_flag = 1 if r["has_no_travel"] else 0
        sev = r["risk_mileage"]["severe_miles"]
        high = r["risk_mileage"]["high_miles"]
        unk = r["risk_mileage"].get("unknown_miles", 0.0)
        # Missing/unmonitored routes must NOT beat monitored routes when hazards are tied.
        # Treat None average_risk_score as 999.0 for sorting.
        avg_risk = (
            r["average_risk_score"]
            if r["average_risk_score"] is not None
            else 999.0
        )
        dur = r["duration_hours"]
        return (safety_flag, sev, high, unk, avg_risk, dur)

    sorted_routes = sorted(routes, key=sort_key)

    # Assign ranks and generate rationale
    for idx, r in enumerate(sorted_routes):
        r["rank"] = idx + 1
        r["is_recommended"] = (idx == 0)

        reasons = []
        if r["has_no_travel"]:
            reasons.append(f"[WARNING] Route contains {r['risk_mileage']['no_travel_miles']} miles of No Travel conditions.")

        if not r["is_weather_complete"]:
            if r["weather_coverage_pct"] == 0.0:
                reasons.append("[NOTICE] Weather forecast data is currently unavailable — safety cannot be fully evaluated.")
            else:
                reasons.append(
                    f"[NOTICE] Incomplete weather coverage ({r['weather_coverage_pct']}% monitored, "
                    f"{r['risk_mileage']['unknown_miles']} mi unmonitored) — safety cannot be fully evaluated."
                )

        if idx == 0:
            # Rationale for winning route
            if r["is_weather_complete"]:
                if not r["has_no_travel"] and r["risk_mileage"]["severe_miles"] == 0 and r["risk_mileage"]["high_miles"] == 0:
                    reasons.append("Safest route: 100% weather coverage with 0 miles of No Travel or Severe conditions.")
                else:
                    reasons.append("Recommended route: Lowest risk route with complete weather coverage.")
            else:
                reasons.append("Recommended route: Lowest risk among evaluated segments (Incomplete weather coverage — safety cannot be fully evaluated).")

            reasons.append(f"1. Fewest Severe miles: {r['risk_mileage']['severe_miles']:.1f} mi")
            reasons.append(f"2. Fewest High-risk miles: {r['risk_mileage']['high_miles']:.1f} mi")
            if r["average_risk_score"] is not None:
                coverage_note = "" if r["is_weather_complete"] else f" ({r['weather_coverage_pct']}% evaluated coverage)"
                reasons.append(f"3. Lowest average risk score: {r['average_risk_score']:.2f}{coverage_note}")
            else:
                reasons.append("3. Average risk score: N/A (no forecast data available)")
            reasons.append(f"4. Estimated travel duration: {r['duration_hours']:.1f} hrs")
        else:
            # Rationale for comparison relative to best route
            best = sorted_routes[0]
            sev_diff = r["risk_mileage"]["severe_miles"] - best["risk_mileage"]["severe_miles"]
            high_diff = r["risk_mileage"]["high_miles"] - best["risk_mileage"]["high_miles"]
            unk_diff = r["risk_mileage"]["unknown_miles"] - best["risk_mileage"]["unknown_miles"]
            dur_diff = r["duration_hours"] - best["duration_hours"]

            if sev_diff > 0:
                reasons.append(f"+{sev_diff:.1f} more Severe miles than recommended route")
            elif high_diff > 0:
                reasons.append(f"+{high_diff:.1f} more High-risk miles than recommended route")
            elif unk_diff > 0:
                reasons.append(f"+{unk_diff:.1f} more unmonitored miles ({r['weather_coverage_pct']}% vs {best['weather_coverage_pct']}%)")
            elif (
                r["average_risk_score"] is not None
                and best["average_risk_score"] is not None
                and r["average_risk_score"] > best["average_risk_score"]
            ):
                reasons.append(f"Higher average risk score ({r['average_risk_score']:.2f} vs {best['average_risk_score']:.2f})")
            elif dur_diff > 0:
                reasons.append(f"+{dur_diff:.1f} hrs longer transit time")
            else:
                reasons.append("Alternative route option")

        r["recommendation_reasons"] = reasons

    return sorted_routes
