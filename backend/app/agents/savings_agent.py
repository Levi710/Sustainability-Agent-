"""Savings agent — wraps run_simulation for each detected behavior."""
from app.services.simulator import run_simulation


def run(behaviors: list[dict]) -> list[dict]:
    results = []
    for b in behaviors:
        result = run_simulation(
            device=b.get("device", "Unknown"),
            current_daily_hours=4.0,
            proposed_daily_hours=3.0,
            shift_to_off_peak=True,
            tariff_rate=8.0,
        )
        results.append(result)
    return results
