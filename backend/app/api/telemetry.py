from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.services.telemetry_engine import start_telemetry, stop_telemetry, get_live_events
from app.agents.pipeline import get_active_node
import asyncio
import json

router = APIRouter()

@router.get("/telemetry/status/{session_id}")
def get_telemetry_status(session_id: str):
    from app.services.telemetry_engine import scheduler
    job_id = f"telemetry_{session_id}"
    is_running = scheduler.get_job(job_id) is not None
    return {
        "is_running": is_running,
        "active_node": get_active_node(session_id)
    }

@router.post("/telemetry/start")
def start(session_id: str, building_type: str, interval_seconds: int = 10):
    start_telemetry(session_id, building_type, interval_seconds)
    return {"status": "started", "session_id": session_id, "interval": interval_seconds}

@router.post("/telemetry/stop")
def stop(session_id: str):
    stop_telemetry(session_id)
    return {"status": "stopped"}

@router.get("/telemetry/stream/{session_id}")
async def stream(session_id: str):
    async def event_generator():
        while True:
            events = get_live_events(session_id)
            if events:
                yield f"data: {json.dumps(events)}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/telemetry/events/{session_id}")
def get_events(session_id: str, limit: int = 50):
    from app.database.connection import SessionLocal
    from app.database.models import TelemetryEvent
    db = SessionLocal()
    events = (
        db.query(TelemetryEvent)
        .filter(TelemetryEvent.session_id == session_id)
        .order_by(TelemetryEvent.timestamp.desc())
        .limit(limit)
        .all()
    )
    db.close()
    return [{"device": e.device, "timestamp": str(e.timestamp), "kwh": e.kwh, "event_type": e.event_type} for e in events]

@router.post("/telemetry/surveillance-snapshot")
def surveillance_snapshot(payload: dict):
    from app.services.surveillance import run_surveillance_snapshot

    session_id = payload.get("session_id")
    if not session_id:
        return {"status": "error", "message": "session_id is required"}

    result = run_surveillance_snapshot(
        session_id=session_id,
        force_anomaly=bool(payload.get("force_anomaly", False)),
        anomaly_probability=float(payload.get("anomaly_probability", 0.15)),
        offline_probability=float(payload.get("offline_probability", 0.08)),
    )
    return {"status": "success", **result}

@router.get("/telemetry/control-signals/{session_id}")
def get_control_signals(session_id: str):
    from app.services.iot_dispatcher import CONTROL_SIGNALS_LOG
    # Filter for current session
    signals = [s for s in CONTROL_SIGNALS_LOG if s["session_id"] == session_id]
    return signals[::-1] # Newest first
