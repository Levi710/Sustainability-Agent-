# Tariff zones (Indian residential electricity pricing)
TARIFF_RATES = {
    "peak": 8.0,       # ₹/kWh  — 6PM to 10PM
    "shoulder": 5.5,   # ₹/kWh  — 6AM to 6PM
    "off_peak": 3.0,   # ₹/kWh  — 10PM to 6AM
}


def get_tariff_zone(hour: int) -> str:
    """Return tariff zone name for a given hour (0–23)."""
    if 18 <= hour < 22:
        return "peak"
    elif hour >= 22 or hour < 6:
        return "off_peak"
    else:
        return "shoulder"


def calculate_cost(kwh: float, hour: int) -> float:
    """Calculate electricity cost in INR for a given kWh reading and hour."""
    zone = get_tariff_zone(hour)
    return round(kwh * TARIFF_RATES[zone], 2)
