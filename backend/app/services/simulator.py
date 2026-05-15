CO2_KG_PER_KWH = 0.82  # Indian grid emission factor (kg CO₂/kWh)


def run_simulation(
    device: str,
    current_daily_hours: float,
    proposed_daily_hours: float,
    shift_to_off_peak: bool,
    tariff_rate: float = 8.0,
) -> dict:
    """
    Simulate energy savings for a given device usage change.

    Returns a dict with: device, monthly_savings_inr, cost_reduction_percent,
    co2_avoided_kg, explanation.
    """
    hours_saved_per_day = current_daily_hours - proposed_daily_hours
    kwh_per_hour = 1.5  # average appliance assumption

    kwh_saved_per_month = hours_saved_per_day * kwh_per_hour * 30

    if shift_to_off_peak:
        # Savings from shifting proposed usage hours to off-peak rate
        effective_tariff_saving = tariff_rate - 3.0
        tariff_savings = proposed_daily_hours * kwh_per_hour * effective_tariff_saving * 30
    else:
        tariff_savings = 0.0

    total_savings_inr = round((kwh_saved_per_month * tariff_rate) + tariff_savings, 2)

    current_monthly_cost = current_daily_hours * kwh_per_hour * 30 * tariff_rate
    cost_reduction_pct = (
        round((total_savings_inr / current_monthly_cost) * 100, 1)
        if current_monthly_cost > 0
        else 0.0
    )

    co2_avoided = round(kwh_saved_per_month * CO2_KG_PER_KWH, 2)

    return {
        "device": device,
        "monthly_savings_inr": total_savings_inr,
        "cost_reduction_percent": cost_reduction_pct,
        "co2_avoided_kg": co2_avoided,
        "explanation": (
            f"Reducing {device} usage by {hours_saved_per_day:.1f} hrs/day saves "
            f"~{kwh_saved_per_month:.1f} kWh/month. "
            f"At ₹{tariff_rate}/kWh that is ₹{total_savings_inr} saved monthly "
            f"and {co2_avoided}kg CO₂ avoided."
        ),
    }
