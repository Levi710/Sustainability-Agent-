import pandas as pd
from app.services.tariff import get_tariff_zone


def detect_habit_patterns(df: pd.DataFrame, critical_devices: list[str]) -> list[dict]:
    """
    Detect recurring behavioural patterns that cause energy waste.

    Returns list of pattern dicts with: pattern, device, frequency,
    confidence, description, and pattern-specific metrics.
    """
    df = df.copy()
    df["hour"] = df["timestamp"].dt.hour
    df["date"] = df["timestamp"].dt.date
    df["tariff_zone"] = df["hour"].apply(get_tariff_zone)

    patterns = []

    # ── Pattern 1: Late-night AC/appliance overuse (11PM–2AM repeated) ──
    late_night = df[(df["hour"] >= 23) | (df["hour"] <= 2)]
    for device in late_night["device"].unique():
        device_data = late_night[late_night["device"] == device]
        unique_days = device_data["date"].nunique()
        if unique_days >= 3:
            avg_kwh = device_data["kwh"].mean()
            patterns.append({
                "pattern": "late_night_overuse",
                "device": device,
                "frequency": f"{unique_days} days",
                "avg_kwh_per_occurrence": round(avg_kwh, 2),
                "confidence": min(0.95, round(unique_days / 10, 2)),
                "description": f"{device} used repeatedly between 11PM–2AM",
            })

    # ── Pattern 2: Peak-hour misuse (6PM–10PM consistent use) ──
    peak_usage = df[df["tariff_zone"] == "peak"]
    for device in peak_usage["device"].unique():
        device_data = peak_usage[peak_usage["device"] == device]
        unique_days = device_data["date"].nunique()
        total_cost = (device_data["kwh"] * 8.0).sum()
        if unique_days >= 4 and total_cost > 100:
            patterns.append({
                "pattern": "peak_hour_misuse",
                "device": device,
                "frequency": f"{unique_days} days",
                "total_peak_cost_inr": round(total_cost, 2),
                "confidence": min(0.92, round(unique_days / 12, 2)),
                "description": (
                    f"{device} consistently used during expensive 6PM–10PM tariff window"
                ),
            })

    # ── Pattern 3: Idle drain (very low but non-zero overnight usage) ──
    overnight = df[(df["hour"] >= 0) & (df["hour"] <= 5)]
    for device in overnight["device"].unique():
        device_data = overnight[overnight["device"] == device]
        avg_kwh = device_data["kwh"].mean()
        unique_days = device_data["date"].nunique()
        if 0.01 < avg_kwh < 0.15 and unique_days >= 5:
            patterns.append({
                "pattern": "idle_drain",
                "device": device,
                "frequency": f"{unique_days} nights",
                "avg_idle_kwh": round(avg_kwh, 3),
                "confidence": min(0.88, round(unique_days / 14, 2)),
                "description": f"{device} consuming standby power every night",
            })

    for pattern in patterns:
        if pattern["device"] in critical_devices:
            pattern["actionable"] = False
            pattern["note"] = "Critical device — pattern logged for monitoring only"
        else:
            pattern["actionable"] = True
            
    return patterns
