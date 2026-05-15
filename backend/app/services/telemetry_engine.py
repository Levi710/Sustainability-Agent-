from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import numpy as np
import json
import random

scheduler = BackgroundScheduler()

# Telemetry simulation config per building type
TELEMETRY_PROFILES = {
    "college": {
        "devices": ["HVAC_Block_A", "Lab_PCs", "Corridor_Lights", "Server_Room_AC", "Canteen_Equipment"],
        "critical": ["Server_Room_AC"],
        "normal_kwh_range": (0.5, 2.0),
        "spike_kwh_range": (3.5, 5.5),
        "spike_probability": 0.15,
        "idle_drain_devices": ["Lab_PCs", "Corridor_Lights"],
        "idle_kwh_range": (0.05, 0.15)
    },
    "house": {
        "devices": ["AC", "Geyser", "Washing_Machine", "Refrigerator", "TV"],
        "critical": ["Refrigerator"],
        "normal_kwh_range": (0.3, 1.5),
        "spike_kwh_range": (2.5, 4.0),
        "spike_probability": 0.12,
        "idle_drain_devices": ["TV"],
        "idle_kwh_range": (0.02, 0.08)
    },
    "commercial_firm": {
        "devices": ["HVAC_Floor1", "HVAC_Floor2", "Workstations", "Server_Room_AC", "Lighting_Main"],
        "critical": ["Server_Room_AC"],
        "normal_kwh_range": (1.0, 3.5),
        "spike_kwh_range": (5.0, 8.0),
        "spike_probability": 0.18,
        "idle_drain_devices": ["Workstations", "Lighting_Main"],
        "idle_kwh_range": (0.1, 0.25)
    },
    "gov_office": {
        "devices": ["HVAC_Main", "HVAC_Server", "Lighting_Floors", "UPS_Bank", "Computers"],
        "critical": ["HVAC_Server", "UPS_Bank"],
        "normal_kwh_range": (0.8, 2.5),
        "spike_kwh_range": (4.0, 6.5),
        "spike_probability": 0.14,
        "idle_drain_devices": ["Lighting_Floors", "Computers"],
        "idle_kwh_range": (0.08, 0.2)
    }
}

active_sessions = {}

def start_telemetry(session_id: str, building_type: str, interval_seconds: int = 10):
    profile = TELEMETRY_PROFILES.get(building_type, TELEMETRY_PROFILES["commercial_firm"])
    active_sessions[session_id] = {
        "building_type": building_type,
        "profile": profile,
        "tick": 0,
        "events": []
    }

    job_id = f"telemetry_{session_id}"
    scheduler.add_job(
        func=_telemetry_tick,
        trigger="interval",
        seconds=interval_seconds,
        id=job_id,
        args=[session_id],
        replace_existing=True
    )
    if not scheduler.running:
        scheduler.start()

def stop_telemetry(session_id: str):
    job_id = f"telemetry_{session_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    active_sessions.pop(session_id, None)

def _get_smart_range(device_name: str):
    """Assigns genuine hardware signatures based on appliance type."""
    name = device_name.lower()
    if "ac" in name or "hvac" in name or "chiller" in name:
        return (1.5, 4.5), 0.2  # (range, spike_prob)
    if "light" in name or "bulb" in name or "led" in name:
        return (0.02, 0.15), 0.05
    if "pc" in name or "computer" in name or "server" in name:
        return (0.2, 0.8), 0.1
    if "geyser" in name or "heater" in name:
        return (2.0, 3.5), 0.15
    return (0.1, 1.0), 0.1 # Default

def _telemetry_tick(session_id: str):
    from app.database.connection import SessionLocal
    from app.database.models import EnergyUsage, TelemetryEvent, BuildingProfile
    from app.services.tariff import get_tariff_zone, calculate_cost
    
    session_data = active_sessions.get(session_id)
    if not session_data:
        return

    db = SessionLocal()
    try:
        # Get actual devices from this session's history
        unique_devices = [d[0] for d in db.query(EnergyUsage.device).filter(EnergyUsage.session_id == session_id).distinct().all()]
        if not unique_devices:
            unique_devices = ["Unknown_Appliance"]

        now = datetime.now()
        hour = now.hour
        tariff_zone = get_tariff_zone(hour)
        anomaly_detected = False
        events_this_tick = []

        # Simulate Virtual Sensors (Random voice/motion triggers)
        sensor_trigger = None
        if random.random() < 0.08:
            sensor_trigger = random.choice(["VOICE_COMMAND_DETECTED", "MOTION_IN_EMPTY_ZONE", "EXTERNAL_GRID_SIGNAL"])

        for device in unique_devices:
            (low, high), spike_prob = _get_smart_range(device)
            
            roll = random.random()
            event_type = "normal"
            
            # Scenario 1: I/O Sensor Triggered behavior
            if sensor_trigger == "VOICE_COMMAND_DETECTED" and "light" in device.lower():
                kwh = high * 0.9 # Simulated turn-on
                event_type = "voice_triggered_on"
            elif sensor_trigger == "MOTION_IN_EMPTY_ZONE" and ("ac" in device.lower() or "light" in device.lower()):
                kwh = high * 1.1 
                event_type = "occupancy_triggered_spike"
                anomaly_detected = True
            # Scenario 2: Natural hardware variance
            elif roll < spike_prob:
                kwh = round(random.uniform(high, high * 2.5), 3)
                event_type = "hardware_malfunction"
                anomaly_detected = True
            else:
                kwh = round(random.uniform(low, high), 3)

            cost = calculate_cost(kwh, hour)
            usage_row = EnergyUsage(
                session_id=session_id, device=device, timestamp=now,
                kwh=kwh, tariff_zone=tariff_zone, cost=cost, is_telemetry=True
            )
            db.add(usage_row)

            tel_event = TelemetryEvent(
                session_id=session_id, device=device, timestamp=now,
                kwh=kwh, event_type=event_type, auto_recommendation_fired=False
            )
            db.add(tel_event)
            events_this_tick.append({"device": device, "kwh": kwh, "event_type": event_type, "sensor": sensor_trigger})

        db.commit()
        if anomaly_detected or sensor_trigger:
            _fire_auto_analysis(session_id, db)
            
    finally:
        db.close()

    session_data["tick"] += 1
    session_data["events"] = events_this_tick

    session_data["tick"] += 1
    session_data["events"] = events_this_tick

def _fire_auto_analysis(session_id: str, db):
    from app.agents.pipeline import run_lightweight_pipeline
    import threading
    threading.Thread(
        target=run_lightweight_pipeline,
        args=(session_id,),
        daemon=True
    ).start()

def get_live_events(session_id: str) -> list:
    return active_sessions.get(session_id, {}).get("events", [])
