from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Form, BackgroundTasks
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
import uuid

from app.database.connection import get_db, SessionLocal
from app.database.models import BuildingProfile, EnergyUsage, Anomaly, Recommendation, AgentLog, DoctorAudit, SessionReport
from app.agents.pipeline import run_pipeline_for_session, ACTIVE_NODES
from app.services.tariff import get_tariff_zone, calculate_cost
import json
import os

router = APIRouter()


def _add_agent_log_once(db: Session, session_id: str, log: dict):
    exists = db.query(AgentLog).filter(
        AgentLog.session_id == session_id,
        AgentLog.agent_name == log.get("agent", ""),
        AgentLog.action == log.get("action", ""),
        AgentLog.output == log.get("output", ""),
    ).first()
    if exists:
        return
    db.add(AgentLog(
        session_id=session_id,
        agent_name=log.get("agent", ""),
        device=log.get("device"),
        action=log.get("action", ""),
        output=log.get("output", ""),
        details=json.dumps(log.get("details", {}), default=str)
    ))


def _add_doctor_audit_once(db: Session, session_id: str, audit: dict):
    exists = db.query(DoctorAudit).filter(
        DoctorAudit.session_id == session_id,
        DoctorAudit.device == audit.get("device", ""),
        DoctorAudit.verification_status == audit.get("verification_status", ""),
        DoctorAudit.doctor_notes == audit.get("doctor_notes", ""),
    ).first()
    if exists:
        return
    db.add(DoctorAudit(
        session_id=session_id,
        device=audit.get("device", ""),
        verification_status=audit.get("verification_status", ""),
        doctor_notes=audit.get("doctor_notes", "")
    ))

@router.post("/building-profile")
def save_building_profile(
    building_type: str = Form(...),
    building_name: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    floors: int = Form(1),
    occupancy_hours: str = Form(""),
    critical_devices: str = Form(""),
    special_constraints: str = Form(""),
    db: Session = Depends(get_db)
):
    session_id = str(uuid.uuid4())
    
    # Process critical devices (split by newline and clean)
    crit_list = [d.strip() for d in critical_devices.split("\n") if d.strip()]
    
    profile = BuildingProfile(
        session_id=session_id,
        building_type=building_type,
        building_name=building_name,
        city=city,
        state=state,
        floors=floors,
        occupancy_hours=occupancy_hours,
        occupancy_peak_days="",
        critical_devices=json.dumps(crit_list),
        special_constraints=special_constraints
    )
    db.add(profile)
    db.commit()
    
    return {"session_id": session_id, "building_type": building_type, "constraint_summary": "Saved"}

@router.post("/upload/csv")
async def upload_csv(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    prompt_overrides: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        contents = await file.read()
        df = pd.read_csv(BytesIO(contents))
        
        # Load registry if it exists (Robust Pathing)
        registry = {}
        # Try both root-relative and local-relative
        registry_paths = ["backend/app/data/device_registry.json", "app/data/device_registry.json"]
        for p in registry_paths:
            if os.path.exists(p):
                with open(p, "r") as f:
                    registry = json.load(f)
                break

        # Flexibly handle columns: allow 'device' OR 'device_id'
        cols = set(df.columns)
        if "device_id" in cols and "device" not in cols:
            # Map ID to Name if possible
            df["device"] = df["device_id"].apply(lambda x: registry.get(x, {}).get("name", x))
        
        if "device_id" in cols and "location" not in cols:
            # Map ID to Location if possible
            df["location"] = df["device_id"].apply(lambda x: registry.get(x, {}).get("location", "Unknown"))
        elif "location" not in cols:
            df["location"] = "Main Building"

        # Corrected validation: Check for device OR device_id
        if not {"timestamp", "kwh"}.issubset(cols) or not ("device" in cols or "device_id" in cols):
            raise HTTPException(status_code=400, detail="CSV must contain: timestamp, kwh, and either 'device' or 'device_id'")
            
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"], format='%Y-%m-%d %H:%M:%S.%f')
        except Exception:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
        df["hour"] = df["timestamp"].dt.hour
        df["tariff_zone"] = df["hour"].apply(get_tariff_zone)
        df["cost"] = df.apply(lambda row: calculate_cost(row["kwh"], row["hour"]), axis=1)
        
        records = []
        for _, row in df.iterrows():
            usage = EnergyUsage(
                session_id=session_id,
                device=row["device"],
                timestamp=row["timestamp"],
                kwh=row["kwh"],
                tariff_zone=row["tariff_zone"],
                cost=row["cost"],
                is_telemetry=False
            )
            records.append(usage)
            
        db.add_all(records)
        db.commit()
        
        # The frontend will now explicitly call /api/analyze to trigger the AI.

        return {"status": "ok", "records_inserted": len(records), "session_id": session_id, "registry_used": bool(registry)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _run_deep_analysis_background(session_id: str, profile: dict, prompt_overrides: dict = None, historical_context: dict = None):
    from app.database.connection import SessionLocal
    from app.database.models import Anomaly, Recommendation, SessionReport
    from app.agents.pipeline import run_pipeline_for_session, ACTIVE_NODES
    import json
    import logging
    logger = logging.getLogger("uvicorn.error")
    
    # Force state to context_node to kick off
    ACTIVE_NODES[session_id] = "context_node"
    
    try:
        result = run_pipeline_for_session(session_id, profile, prompt_overrides=prompt_overrides, historical_context=historical_context)
        
        db = SessionLocal()
        try:
            # Save anomalies
            for a in result.get("anomalies", []):
                db_anomaly = Anomaly(
                    session_id=session_id,
                    device=a["device"],
                    timestamp=a["timestamp"],
                    severity=a["severity"],
                    reason=a["reason"],
                    estimated_loss=a["estimated_loss"],
                    confidence=a["confidence"],
                    is_critical_device=a.get("is_critical_device", False)
                )
                db.add(db_anomaly)
                
            # Save recommendations
            for rec in result.get("recommendations", []):
                db_rec = Recommendation(
                    session_id=session_id,
                    issue=rec.get("issue", ""),
                    reason=rec.get("reason", ""),
                    reasoning_proof=rec.get("reasoning_proof", ""),
                    control_action=rec.get("control_action", ""),
                    estimated_monthly_loss=rec.get("estimated_monthly_loss", ""),
                    recommendation=rec.get("recommendation", ""),
                    projected_savings=0.0,
                    confidence=rec.get("confidence", 0.9),
                    triggered_by="upload"
                )
                db.add(db_rec)
                
            # Save doctor audits
            for audit in result.get("doctor_audits", []):
                _add_doctor_audit_once(db, session_id, audit)

            report = result.get("analysis_report", {}) or {}
            final_explanation = result.get("final_explanation") or report.get("final_explanation") or ""
            if final_explanation or report:
                db.add(SessionReport(
                    session_id=session_id,
                    final_explanation=final_explanation,
                    summary_json=json.dumps(report, default=str),
                ))
                
            db.commit()
        except Exception as db_e:
            logger.error(f"Error saving background analysis DB records: {db_e}")
        finally:
            db.close()
    except Exception as pipeline_e:
        logger.error(f"Background pipeline failed: {pipeline_e}")
    finally:
        ACTIVE_NODES[session_id] = "Idle"


@router.post("/analyze")
def analyze(payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
        
    profile_row = db.query(BuildingProfile).filter(BuildingProfile.session_id == session_id).first()
    if not profile_row:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    profile = {
        "building_type": profile_row.building_type,
        "building_name": profile_row.building_name,
        "city": profile_row.city,
        "state": profile_row.state,
        "occupancy_hours": profile_row.occupancy_hours,
        "critical_devices": profile_row.critical_devices,
        "special_constraints": profile_row.special_constraints
    }
    
    usage_count = db.query(EnergyUsage).filter(EnergyUsage.session_id == session_id).count()
    if usage_count == 0:
        raise HTTPException(status_code=400, detail="No usage data found")
        
    # Fetch Historical Context
    past_recs = db.query(Recommendation).filter(Recommendation.session_id == session_id).all()
    past_anoms = db.query(Anomaly).filter(Anomaly.session_id == session_id).all()
    
    historical_context = {
        "past_recommendations": [r.issue for r in past_recs],
        "past_anomaly_count": len(past_anoms),
        "total_data_points": usage_count
    }
    
    # Launch in background
    background_tasks.add_task(
        _run_deep_analysis_background, 
        session_id, 
        profile, 
        payload.get("prompt_overrides"), 
        historical_context
    )
    
    return {
        "status": "processing", 
        "message": "Deep analysis started in background."
    }

@router.get("/recommendations/{session_id}")
def get_recommendations(session_id: str, db: Session = Depends(get_db)):
    recs = db.query(Recommendation).filter(Recommendation.session_id == session_id).order_by(Recommendation.created_at.desc()).all()
    return [
        {
            "issue": r.issue, 
            "reason": r.reason, 
            "recommendation": r.recommendation, 
            "estimated_monthly_loss": r.estimated_monthly_loss, 
            "triggered_by": r.triggered_by,
            "confidence": r.confidence,
            "reasoning_proof": r.reasoning_proof,
            "control_action": r.control_action
        } for r in recs
    ]

@router.get("/anomalies/{session_id}")
def get_anomalies(session_id: str, db: Session = Depends(get_db)):
    anomalies = (
        db.query(Anomaly)
        .filter(Anomaly.session_id == session_id)
        .order_by(Anomaly.timestamp.desc())
        .all()
    )
    return [
        {
            "device": a.device,
            "timestamp": str(a.timestamp),
            "severity": a.severity,
            "reason": a.reason,
            "estimated_loss": a.estimated_loss,
            "confidence": a.confidence,
            "is_critical_device": a.is_critical_device,
        }
        for a in anomalies
    ]

@router.get("/dashboard-state/{session_id}")
def get_dashboard_state(session_id: str, db: Session = Depends(get_db)):
    # 1. Fetch Recommendations
    recs = db.query(Recommendation).filter(Recommendation.session_id == session_id).all()
    rec_list = [
        {
            "issue": r.issue,
            "recommendation": r.recommendation,
            "triggered_by": r.triggered_by,
            "estimated_monthly_loss": r.estimated_monthly_loss or "N/A",
            "confidence": r.confidence or 0.0,
            "control_action": r.control_action
        }
        for r in recs
    ]
    
    # 2. Fetch Anomalies
    anomalies = db.query(Anomaly).filter(Anomaly.session_id == session_id).order_by(Anomaly.timestamp.desc()).limit(10).all()
    anom_list = [{"device": a.device, "reason": a.reason, "severity": a.severity} for a in anomalies]
    
    # 3. Fetch Logs
    logs = db.query(AgentLog).filter(AgentLog.session_id == session_id).order_by(AgentLog.created_at.desc()).limit(100).all()
    log_list = []
    for l in logs:
        try:
            details = json.loads(l.details or "{}")
        except json.JSONDecodeError:
            details = {}
        log_list.append({
            "agent": l.agent_name,
            "device": l.device,
            "action": l.action,
            "output": l.output,
            "details": details,
            "timestamp": str(l.created_at),
        })
    
    # 4. Fetch Audits
    audits = db.query(DoctorAudit).filter(DoctorAudit.session_id == session_id).order_by(DoctorAudit.created_at.desc()).limit(10).all()
    audit_list = [{"device": a.device, "verification_status": a.verification_status, "doctor_notes": a.doctor_notes} for a in audits]

    # 5. Fetch latest explanation report
    report = db.query(SessionReport).filter(SessionReport.session_id == session_id).order_by(SessionReport.created_at.desc()).first()
    report_payload = {}
    if report:
        try:
            report_payload = json.loads(report.summary_json or "{}")
        except json.JSONDecodeError:
            report_payload = {}
        report_payload["final_explanation"] = report.final_explanation

    # 6. Fetch Active Node and IoT Control Signals
    from app.agents.pipeline import get_active_node
    from app.services.iot_dispatcher import CONTROL_SIGNALS_LOG
    active_node = get_active_node(session_id)
    signals = [s for s in CONTROL_SIGNALS_LOG if s.get("session_id") == session_id]
    signals = signals[::-1]

    return {
        "recommendations": rec_list,
        "anomalies": anom_list,
        "logs": log_list,
        "audits": audit_list,
        "report": report_payload,
        "active_node": active_node,
        "control_signals": signals
    }

@router.get("/intelligence/{session_id}")
def get_intelligence(session_id: str, db: Session = Depends(get_db)):
    logs = db.query(AgentLog).filter(AgentLog.session_id == session_id).order_by(AgentLog.created_at.desc()).all()
    audits = db.query(DoctorAudit).filter(DoctorAudit.session_id == session_id).order_by(DoctorAudit.created_at.desc()).all()
    
    # Group logs by agent and cap at 5 per device (or overall per agent if no device)
    grouped_logs = {}
    counts = {} # Tracks (agent, device) counts
    
    for l in logs:
        agent = l.agent_name
        device = l.device or "General"
        key = (agent, device)
        
        if agent not in grouped_logs:
            grouped_logs[agent] = []
        
        if counts.get(key, 0) < 5:
            grouped_logs[agent].append({
                "agent": agent,
                "device": l.device,
                "action": l.action,
                "output": l.output,
                "timestamp": l.created_at.strftime("%H:%M:%S") if l.created_at else "N/A",
                "details": json.loads(l.details or "{}")
            })
            counts[key] = counts.get(key, 0) + 1
    
    return {
        "grouped_logs": grouped_logs,
        "doctor_audits": [{"device": a.device, "verification_status": a.verification_status, "doctor_notes": a.doctor_notes, "timestamp": a.created_at.strftime("%H:%M:%S") if a.created_at else "N/A"} for a in audits]
    }

@router.get("/data/{session_id}")
def get_session_data(session_id: str, db: Session = Depends(get_db)):
    usage = db.query(EnergyUsage).filter(EnergyUsage.session_id == session_id).order_by(EnergyUsage.timestamp.asc()).all()
    return {"data": [{"timestamp": str(u.timestamp), "device": u.device, "kwh": u.kwh} for u in usage]}

@router.delete("/data/{session_id}")
def delete_data(session_id: str, db: Session = Depends(get_db)):
    from app.database.models import TelemetryEvent
    db.query(EnergyUsage).filter(EnergyUsage.session_id == session_id).delete()
    db.query(Anomaly).filter(Anomaly.session_id == session_id).delete()
    db.query(Recommendation).filter(Recommendation.session_id == session_id).delete()
    db.query(BuildingProfile).filter(BuildingProfile.session_id == session_id).delete()
    db.query(TelemetryEvent).filter(TelemetryEvent.session_id == session_id).delete()
    db.commit()
    return {"status": "deleted"}
