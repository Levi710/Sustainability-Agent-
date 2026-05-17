import json
import random
import threading
from datetime import datetime
from pathlib import Path

from app.database.connection import SessionLocal
from app.database.models import AgentLog, EnergyUsage, TelemetryEvent
from app.services.tariff import calculate_cost, get_tariff_zone


def load_device_registry() -> dict:
    candidates = [
        Path("backend/app/data/device_registry.json"),
        Path("app/data/device_registry.json"),
        Path(__file__).resolve().parents[1] / "data" / "device_registry.json",
    ]
    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
    return {}


def _normal_kwh_for_device(meta: dict) -> tuple[float, float]:
    device_type = str(meta.get("type", "")).lower()
    if "hvac" in device_type or "ac" in device_type or "chiller" in device_type:
        return 1.5, 4.5
    if "light" in device_type:
        return 0.03, 0.25
    if "it" in device_type or "server" in device_type:
        return 0.5, 2.0
    if "fan" in device_type:
        return 0.05, 0.3
    return 0.1, 1.0


def run_surveillance_snapshot(
    session_id: str,
    force_anomaly: bool = False,
    anomaly_probability: float = 0.15,
    offline_probability: float = 0.08,
) -> dict:
    """
    Poll all registered IoT devices once.

    This models the missing surveillance layer: every device is expected to report.
    Non-response is treated as a maintenance/manual-inspection event, not just an
    energy anomaly.
    """
    registry = load_device_registry()
    if not registry:
        registry = {
            "HVAC_Block_A": {"name": "HVAC Block A", "type": "HVAC", "floor": "Floor 1", "criticality": "medium"},
            "Lighting_Main": {"name": "Main Lighting", "type": "Lighting", "floor": "Floor 1", "criticality": "low"},
        }

    now = datetime.now()
    hour = now.hour
    tariff_zone = get_tariff_zone(hour)
    events = []
    offline_devices = []
    anomaly_devices = []

    db = SessionLocal()
    try:
        forced_anomaly_index = random.randrange(len(registry)) if force_anomaly and registry else None

        for idx, (device_id, meta) in enumerate(registry.items()):
            responded = random.random() > offline_probability
            low, high = _normal_kwh_for_device(meta)
            event_type = "normal"

            if not responded:
                kwh = 0.0
                event_type = "not_responding"
                offline_devices.append(device_id)
            else:
                should_spike = idx == forced_anomaly_index or random.random() < anomaly_probability
                if should_spike:
                    kwh = round(random.uniform(high * 1.8, high * 3.0), 3)
                    event_type = "surveillance_anomaly"
                    anomaly_devices.append(device_id)
                else:
                    kwh = round(random.uniform(low, high), 3)

            db.add(EnergyUsage(
                session_id=session_id,
                device=device_id,
                timestamp=now,
                kwh=kwh,
                tariff_zone=tariff_zone,
                cost=calculate_cost(kwh, hour),
                is_telemetry=True,
            ))
            db.add(TelemetryEvent(
                session_id=session_id,
                device=device_id,
                timestamp=now,
                kwh=kwh,
                event_type=event_type,
                auto_recommendation_fired=event_type != "normal",
            ))
            events.append({
                "device_id": device_id,
                "name": meta.get("name", device_id),
                "type": meta.get("type", "UNKNOWN"),
                "floor": meta.get("floor", "Unknown"),
                "criticality": meta.get("criticality", "unknown"),
                "responded": responded,
                "kwh": kwh,
                "event_type": event_type,
            })

        summary = {
            "devices_checked": len(events),
            "responding": sum(1 for e in events if e["responded"]),
            "offline_devices": offline_devices,
            "anomaly_devices": anomaly_devices,
            "triggered_pipeline": bool(offline_devices or anomaly_devices),
            "anomaly_probability": anomaly_probability,
            "offline_probability": offline_probability,
        }

        db.add(AgentLog(
            session_id=session_id,
            agent_name="Surveillance Agent",
            action="Full IoT Registry Poll",
            output=(
                f"Polled {summary['devices_checked']} devices. "
                f"{summary['responding']} responded, {len(offline_devices)} offline, "
                f"{len(anomaly_devices)} anomalous."
            ),
            details=json.dumps({"summary": summary, "events": events}, default=str),
        ))
        db.commit()

        if summary["triggered_pipeline"]:
            from app.agents.pipeline import run_lightweight_pipeline

            threading.Thread(target=run_lightweight_pipeline, args=[session_id], daemon=True).start()

        return {"summary": summary, "events": events}
    finally:
        db.close()
