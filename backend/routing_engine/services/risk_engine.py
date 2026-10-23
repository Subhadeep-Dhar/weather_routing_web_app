"""
Weather risk classification and cargo-weight override engine for Spotter Truck Routing.

Risk Rules & Thresholds:
- Wind:
    Low:       < 25 mph
    Moderate:  25 to <35 mph (25–34)
    High:      35 to <45 mph (35–44)
    Severe:    45 to <55 mph (45–54)
    No Travel: >= 55 mph

- Rain (in/hr):
    Low:       < 0.10 in/hr
    Moderate:  0.10 to <0.25 in/hr (0.10–0.25)
    High:      0.25 to <0.50 in/hr (0.25–0.50)
    Severe:    0.50 to <=1.00 in/hr (0.50–1.00)
    No Travel: > 1.00 in/hr

- Snow (in/hr):
    Low:       < 0.5 in/hr
    Moderate:  0.5 to <1.0 in/hr (0.5–1.0)
    High:      1.0 to <2.0 in/hr (1.0–2.0)
    Severe:    2.0 to <=3.0 in/hr (2.0–3.0)
    No Travel: > 3.0 in/hr

Cargo-Weight Overrides:
- Wind >= 55 mph -> No Travel for any load
- Wind 45–54 mph (Severe) AND cargo > 30,000 lb -> No Travel
- Wind 35–44 mph (High) AND cargo > 40,000 lb -> Severe
"""

from typing import Dict, Any, Tuple, Optional
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    SEVERE = "Severe"
    NO_TRAVEL = "No Travel"
    UNKNOWN = "Unknown"


# Ordinal mapping for numeric average risk calculation
RISK_ORDINAL_MAP = {
    RiskLevel.LOW: 1.0,
    RiskLevel.MODERATE: 2.0,
    RiskLevel.HIGH: 3.0,
    RiskLevel.SEVERE: 4.0,
    RiskLevel.NO_TRAVEL: 5.0,
    RiskLevel.UNKNOWN: 0.0,
}

ORDINAL_TO_RISK = {
    0: RiskLevel.UNKNOWN,
    1: RiskLevel.LOW,
    2: RiskLevel.MODERATE,
    3: RiskLevel.HIGH,
    4: RiskLevel.SEVERE,
    5: RiskLevel.NO_TRAVEL,
}


def classify_wind(wind_mph: float) -> RiskLevel:
    """Classifies wind speed into Low, Moderate, High, Severe, or No Travel."""
    if wind_mph < 0:
        raise ValueError(f"Wind speed cannot be negative: {wind_mph}")
    if wind_mph < 25.0:
        return RiskLevel.LOW
    elif wind_mph < 35.0:
        return RiskLevel.MODERATE
    elif wind_mph < 45.0:
        return RiskLevel.HIGH
    elif wind_mph < 55.0:
        return RiskLevel.SEVERE
    else:
        return RiskLevel.NO_TRAVEL


def classify_rain(rain_in_hr: float) -> RiskLevel:
    """Classifies rain precipitation intensity (in/hr)."""
    if rain_in_hr < 0:
        raise ValueError(f"Rain intensity cannot be negative: {rain_in_hr}")
    if rain_in_hr < 0.10:
        return RiskLevel.LOW
    elif rain_in_hr < 0.25:
        return RiskLevel.MODERATE
    elif rain_in_hr < 0.50:
        return RiskLevel.HIGH
    elif rain_in_hr <= 1.00:
        return RiskLevel.SEVERE
    else:
        return RiskLevel.NO_TRAVEL


def classify_snow(snow_in_hr: float) -> RiskLevel:
    """Classifies snow precipitation intensity (in/hr)."""
    if snow_in_hr < 0:
        raise ValueError(f"Snow intensity cannot be negative: {snow_in_hr}")
    if snow_in_hr < 0.5:
        return RiskLevel.LOW
    elif snow_in_hr < 1.0:
        return RiskLevel.MODERATE
    elif snow_in_hr < 2.0:
        return RiskLevel.HIGH
    elif snow_in_hr <= 3.0:
        return RiskLevel.SEVERE
    else:
        return RiskLevel.NO_TRAVEL


def apply_cargo_overrides(
    wind_risk: RiskLevel,
    wind_mph: float,
    cargo_weight_lbs: float,
) -> Tuple[RiskLevel, Optional[str]]:
    """
    Applies cargo weight overrides to wind risk according to assessment rules:
    - >=55 mph -> No Travel for any load
    - 45–54 mph + >30,000 lb -> No Travel
    - 35–44 mph + >40,000 lb -> Severe

    Returns:
        (effective_wind_risk, override_reason_or_none)
    """
    if cargo_weight_lbs < 0:
        raise ValueError(f"Cargo weight cannot be negative: {cargo_weight_lbs}")

    if wind_mph >= 55.0:
        return RiskLevel.NO_TRAVEL, "Wind ≥ 55 mph: No Travel for any load"

    if 45.0 <= wind_mph < 55.0:
        if cargo_weight_lbs > 30000.0:
            return (
                RiskLevel.NO_TRAVEL,
                f"Wind {wind_mph:.1f} mph (45–54 mph) + cargo {cargo_weight_lbs:,.0f} lb (>30,000 lb) → No Travel override",
            )
        return RiskLevel.SEVERE, None

    if 35.0 <= wind_mph < 45.0:
        if cargo_weight_lbs > 40000.0:
            return (
                RiskLevel.SEVERE,
                f"Wind {wind_mph:.1f} mph (35–44 mph) + cargo {cargo_weight_lbs:,.0f} lb (>40,000 lb) → Severe override",
            )
        return RiskLevel.HIGH, None

    return wind_risk, None


def evaluate_checkpoint_risk(
    wind_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    cargo_weight_lbs: float,
) -> Dict[str, Any]:
    """
    Evaluates weather risk for a checkpoint including raw classifications,
    cargo-weight overrides, and combined effective risk.
    """
    base_wind_risk = classify_wind(wind_mph)
    effective_wind_risk, cargo_override_reason = apply_cargo_overrides(
        base_wind_risk, wind_mph, cargo_weight_lbs
    )
    rain_risk = classify_rain(rain_in_hr)
    snow_risk = classify_snow(snow_in_hr)

    # Combined risk: maximum risk among hazards (preserves the most dangerous condition)
    # If any is No Travel -> No Travel
    risks = [effective_wind_risk, rain_risk, snow_risk]
    max_risk = max(risks, key=lambda r: RISK_ORDINAL_MAP[r])

    return {
        "raw_wind_risk": base_wind_risk.value,
        "effective_wind_risk": effective_wind_risk.value,
        "rain_risk": rain_risk.value,
        "snow_risk": snow_risk.value,
        "cargo_override_reason": cargo_override_reason,
        "effective_risk": max_risk.value,
        "risk_score": RISK_ORDINAL_MAP[max_risk],
    }
