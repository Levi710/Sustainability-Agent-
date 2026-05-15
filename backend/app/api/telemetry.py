from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.services.telemetry_engine import start_telemetry, stop_telemetry, get_live_events
from app.agents.pipeline import get_active_node
import asyncio
import json

router = APIRouter()

@router.get("/telemetry/status/{session_id}")
async def get_telemetry_status(session_id: str):
    return {"active_node": get_active_node(session_id)}

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
