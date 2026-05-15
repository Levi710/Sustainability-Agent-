from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Form
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
import uuid

from app.database.connection import get_db
from app.database.models import BuildingProfile, EnergyUsage, Anomaly, Recommendation
from app.agents.pipeline import run_pipeline_for_session
from app.services.tariff import get_tariff_zone, calculate_cost
import json

router = APIRouter()

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
) :
    try:
        contents = await file.read()
        df = pd.read_csv(BytesIO(contents))
        
        required_cols = {"timestamp", "device", "kwh", "location"}
        if not required_cols.issubset(set(df.columns)):
            raise HTTPException(status_code=400, detail=f"CSV must contain columns: {required_cols}")
            
        df["timestamp"] = pd.to_datetime(df["timestamp"])
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
        
        return {"status": "ok", "records_inserted": len(records), "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
def analyze(payload: dict, db: Session = Depends(get_db)):
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
    
    usage = db.query(EnergyUsage).filter(EnergyUsage.session_id == session_id).order_by(EnergyUsage.timestamp.desc()).limit(10000).all()
    if not usage:
        raise HTTPException(status_code=400, detail="No usage data found")
        
    raw_data = [{"timestamp": u.timestamp, "device": u.device, "kwh": u.kwh, "location": "Unknown"} for u in usage]
    
    # Fetch Historical Context
    past_recs = db.query(Recommendation).filter(Recommendation.session_id == session_id).all()
    past_anoms = db.query(Anomaly).filter(Anomaly.session_id == session_id).all()
    
    historical_context = {
        "past_recommendations": [r.issue for r in past_recs],
        "past_anomaly_count": len(past_anoms),
        "total_data_points": len(usage)
    }
    
    result = run_pipeline_for_session(session_id, profile, prompt_overrides=payload.get("prompt_overrides"), historical_context=historical_context)
    
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
    from app.database.models import AgentLog, DoctorAudit
    import json
    
    for i, rec in enumerate(result.get("recommendations", [])):
        # Proactively mark high-confidence items as 'telemetry_auto' to show action
        is_auto = i == 0 or rec.get("confidence", 0) > 0.85
        
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
            triggered_by="telemetry_auto" if is_auto else "upload"
        )
        db.add(db_rec)
        
    # Save agent reasoning traces
    for log in result.get("agent_logs", []):
        db_log = AgentLog(
            session_id=session_id,
            agent_name=log.get("agent", ""),
            action=log.get("action", ""),
            output=log.get("output", ""),
            details=json.dumps(log.get("details", {}), default=str)
        )
        db.add(db_log)
        
    # Save doctor audits
    for audit in result.get("doctor_audits", []):
        db_audit = DoctorAudit(
            session_id=session_id,
            device=audit.get("device", ""),
            verification_status=audit.get("verification_status", ""),
            doctor_notes=audit.get("doctor_notes", "")
        )
        db.add(db_audit)
        
    db.commit()
    
    return {
        "status": "success", 
        "report": result.get("analysis_report"), 
        "agent_logs": result.get("agent_logs"),
        "domain_research": result.get("domain_research")
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
    anomalies = db.query(Anomaly).filter(Anomaly.session_id == session_id).order_by(Anomaly.timestamp.desc()).limit(100).all()
    return [{"device": a.device, "timestamp": str(a.timestamp), "severity": a.severity, "reason": a.reason, "is_critical_device": a.is_critical_device} for a in anomalies]

@router.get("/intelligence/{session_id}")
def get_intelligence(session_id: str, db: Session = Depends(get_db)):
    logs = db.query(AgentLog).filter(AgentLog.session_id == session_id).order_by(AgentLog.created_at.asc()).all()
    audits = db.query(DoctorAudit).filter(DoctorAudit.session_id == session_id).order_by(DoctorAudit.created_at.desc()).all()
    
    return {
        "agent_logs": [{"agent": l.agent_name, "action": l.action, "output": l.output, "details": json.loads(l.details or "{}")} for l in logs],
        "doctor_audits": [{"device": a.device, "verification_status": a.verification_status, "doctor_notes": a.doctor_notes} for a in audits]
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
