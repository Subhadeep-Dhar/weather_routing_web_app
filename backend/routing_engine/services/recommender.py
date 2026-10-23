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


def calculate_route_metrics(route_id: str, name: str, distance_miles: float, duration_hours: float, checkpoints: List[Dict[str, Any]], geometry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggregates checkpoint risk classifications and segment distances into comprehensive route metrics.
    Ensures exact distance reconciliation.
    """
    low_miles = 0.0
    mod_miles = 0.0
    high_miles = 0.0
    sev_miles = 0.0
    no_travel_miles = 0.0

    weighted_risk_sum = 0.0
    total_segment_dist = 0.0

    has_no_travel = False
    highest_severity_encountered = RiskLevel.LOW

    for cp in checkpoints:
        seg_dist = cp.get("segment_distance_miles", 0.0)
        risk_str = cp.get("effective_risk", RiskLevel.LOW.value)
        risk_score = cp.get("risk_score", 1.0)

        total_segment_dist += seg_dist
        weighted_risk_sum += (seg_dist * risk_score)

        if risk_str == RiskLevel.NO_TRAVEL.value:
            no_travel_miles += seg_dist
            has_no_travel = True
            highest_severity_encountered = RiskLevel.NO_TRAVEL
        elif risk_str == RiskLevel.SEVERE.value:
            sev_miles += seg_dist
            if highest_severity_encountered != RiskLevel.NO_TRAVEL:
                highest_severity_encountered = RiskLevel.SEVERE
        elif risk_str == RiskLevel.HIGH.value:
            high_miles += seg_dist
            if highest_severity_encountered in [RiskLevel.LOW, RiskLevel.MODERATE]:
                highest_severity_encountered = RiskLevel.HIGH
        elif risk_str == RiskLevel.MODERATE.value:
            mod_miles += seg_dist
            if highest_severity_encountered == RiskLevel.LOW:
                highest_severity_encountered = RiskLevel.MODERATE
        else:
            low_miles += seg_dist

    # Distance-weighted average risk score
    avg_risk_score = round(weighted_risk_sum / total_segment_dist, 2) if total_segment_dist > 0 else 1.0

    # Ensure total accounted miles equals distance_miles
    total_accounted = round(low_miles + mod_miles + high_miles + sev_miles + no_travel_miles, 2)

    return {
        "route_id": route_id,
        "name": name,
        "distance_miles": round(distance_miles, 1),
        "duration_hours": round(duration_hours, 2),
        "geometry": geometry,
        "checkpoints": checkpoints,
        "checkpoint_count": len(checkpoints),
        "has_no_travel": has_no_travel,
        "overall_classification": highest_severity_encountered.value,
        "risk_mileage": {
            "low_miles": round(low_miles, 1),
            "moderate_miles": round(mod_miles, 1),
            "high_miles": round(high_miles, 1),
            "severe_miles": round(sev_miles, 1),
            "no_travel_miles": round(no_travel_miles, 1),
            "total_accounted_miles": total_accounted,
        },
        "average_risk_score": avg_risk_score,
        "recommendation_reasons": [],
        "is_recommended": False,
        "rank": 0,
    }


def rank_and_recommend_routes(routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ranks routes using strict lexicographical priority order:
    Primary safety flag: has_no_travel (False < True)
    Tier 1: Fewest Severe miles
    Tier 2: Fewest High-risk miles
    Tier 3: Lowest average risk
    Tier 4: Shortest travel time (duration_hours)

    Returns routes sorted from best (rank 1) to worst, with recommendation explanations.
    """
    if not routes:
        return []

    def sort_key(r: Dict[str, Any]) -> Tuple[int, float, float, float, float]:
        # Flag 0 for safe (no travel == 0), 1 for unsafe
        safety_flag = 1 if r["has_no_travel"] else 0
        sev = r["risk_mileage"]["severe_miles"]
        high = r["risk_mileage"]["high_miles"]
        avg_risk = r["average_risk_score"]
        dur = r["duration_hours"]
        return (safety_flag, sev, high, avg_risk, dur)

    sorted_routes = sorted(routes, key=sort_key)

    # Assign ranks and generate rationale
    for idx, r in enumerate(sorted_routes):
        r["rank"] = idx + 1
        r["is_recommended"] = (idx == 0)

        reasons = []
        if r["has_no_travel"]:
            reasons.append(f"[WARNING] Route contains {r['risk_mileage']['no_travel_miles']} miles of No Travel conditions.")

        if idx == 0:
            # Rationale for winning route
            if not r["has_no_travel"]:
                reasons.append("Safest route: 0 miles of No Travel conditions.")
            reasons.append(f"1. Fewest Severe miles: {r['risk_mileage']['severe_miles']:.1f} mi")
            reasons.append(f"2. Fewest High-risk miles: {r['risk_mileage']['high_miles']:.1f} mi")
            reasons.append(f"3. Lowest average risk score: {r['average_risk_score']:.2f}")
            reasons.append(f"4. Estimated travel duration: {r['duration_hours']:.1f} hrs")
        else:
            # Rationale for comparison relative to best route
            best = sorted_routes[0]
            sev_diff = r["risk_mileage"]["severe_miles"] - best["risk_mileage"]["severe_miles"]
            high_diff = r["risk_mileage"]["high_miles"] - best["risk_mileage"]["high_miles"]
            dur_diff = r["duration_hours"] - best["duration_hours"]

            if sev_diff > 0:
                reasons.append(f"+{sev_diff:.1f} more Severe miles than recommended route")
            elif high_diff > 0:
                reasons.append(f"+{high_diff:.1f} more High-risk miles than recommended route")
            elif r["average_risk_score"] > best["average_risk_score"]:
                reasons.append(f"Higher average risk score ({r['average_risk_score']:.2f} vs {best['average_risk_score']:.2f})")
            elif dur_diff > 0:
                reasons.append(f"+{dur_diff:.1f} hrs longer transit time")
            else:
                reasons.append("Alternative route option")

        r["recommendation_reasons"] = reasons

    return sorted_routes
