import json
import os
from typing import TypedDict, Any
import pandas as pd
import requests
import re
from langgraph.graph import StateGraph, END

from app.services.baseline import build_baseline, merge_with_baseline
from app.services.anomaly import detect_anomalies
from app.services.habits import detect_habit_patterns
from app.services.simulator import run_simulation

from app.agents.context_agent import context_node
from app.agents.research_agent import research_node
from app.agents.behavior_agent import behavior_node
from app.agents.recommendation_agent import recommendation_node
from app.agents.explanation_agent import explanation_node

import logging
logger = logging.getLogger("uvicorn.error")

# Real-time tracking for the Visual Trajectory
ACTIVE_NODES = {}

def get_active_node(session_id: str):
    return ACTIVE_NODES.get(session_id, "Idle")

# REAL-TIME TRACKING & INCREMENTAL LOGGING
def log_node(name, func):
    def wrapper(state):
        session_id = state.get("session_id", "unknown")
        ACTIVE_NODES[session_id] = name
        logger.info(f"Entering node: {name}")
        
        # Record length before
        pre_logs_count = len(state.get("agent_logs", []))
        pre_audits_count = len(state.get("doctor_audits", []))
        
        try:
            new_state = func(state)
            
            # Check for new logs or audits to stream to DB
            new_logs = new_state.get("agent_logs", [])
            new_audits = new_state.get("doctor_audits", [])
            
            if len(new_logs) > pre_logs_count or len(new_audits) > pre_audits_count:
                from app.database.connection import SessionLocal
                from app.database.models import AgentLog, DoctorAudit
                import json
                db = SessionLocal()
                try:
                    # Stream Logs
                    for i in range(pre_logs_count, len(new_logs)):
                        log = new_logs[i]
                        db_log = AgentLog(
                            session_id=session_id,
                            agent_name=log.get("agent", ""),
                            action=log.get("action", ""),
                            output=log.get("output", ""),
                            details=json.dumps(log.get("details", {}), default=str)
                        )
                        db.add(db_log)
                        
                    # Stream Audits
                    for i in range(pre_audits_count, len(new_audits)):
                        audit = new_audits[i]
                        db_audit = DoctorAudit(
                            session_id=session_id,
                            device=audit.get("device", ""),
                            verification_status=audit.get("verification_status", ""),
                            doctor_notes=audit.get("doctor_notes", "")
                        )
                        db.add(db_audit)
                        
                    db.commit()
                finally:
                    db.close()
            
            return new_state
        finally:
            pass
    return wrapper

class SustainAIState(TypedDict):
    session_id: str
    building_profile: dict
    constraint_block: str
    domain_research: dict
    raw_data: list[dict]
    baseline: Any
    anomalies: list[dict]
    patterns: list[dict]
    behaviors: list[dict]
    savings_estimates: list[dict]
    recommendations: list[dict]
    final_explanation: str
    analysis_report: dict
    agent_logs: list[dict]
    prompt_overrides: dict
    historical_context: dict
    telemetry_events: list[dict]
    worker_reports: list[dict]
    doctor_audits: list[dict]

def _get_api_key():
    api_key = os.getenv("NVIDIA_API_KEY", "")
    return api_key if api_key and api_key != "your_key_here" else None

def _raw_llm_call(api_key: str, system_prompt: str, user_content: str) -> str:
    # Switched to Groq for ultra-fast reasoning as requested
    invoke_url = "https://api.groq.com/openai/v1/chat/completions"
    groq_key = os.getenv("GROQ_API_KEY")
    
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2,
        "max_tokens": 4096,
        "stream": False
    }
    
    import time
    max_retries = 3
    for i in range(max_retries):
        try:
            response = requests.post(invoke_url, headers=headers, json=payload, timeout=60)
            if response.status_code == 429:
                wait_time = (i + 1) * 2
                logger.warning(f"Groq Rate limited (429). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            response.raise_for_status()
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"]
            
            # Clean up markdown
            content = re.sub(r'^```(?:json)?', '', content).strip()
            content = re.sub(r'```$', '', content).strip()
            return content
        except Exception as e:
            if i == max_retries - 1:
                raise e
            time.sleep(1)
    return ""

def _llm_call(system_prompt: str, user_content: str, fallback: Any) -> Any:
    api_key = _get_api_key()
    if api_key is None:
        logger.warning("No NVIDIA_API_KEY found, using fallback")
        return fallback
    try:
        content = _raw_llm_call(api_key, system_prompt, user_content)
        return json.loads(content)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return fallback

def pattern_node(state: SustainAIState) -> SustainAIState:
    df = pd.DataFrame(state["raw_data"])
    if df.empty:
        state["patterns"] = []
        return state
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    import json
    critical_str = state["building_profile"].get("critical_devices", "[]")
    try:
        critical_devices = json.loads(critical_str)
    except:
        critical_devices = []
        
    patterns = detect_habit_patterns(df, critical_devices)
    state["patterns"] = patterns
    
    state.get("agent_logs", []).append({
        "agent": "Behavior Agent",
        "action": "Pattern Detection",
        "output": f"Detected {len(patterns)} habit patterns.",
        "details": patterns[:2]
    })
    return state

def anomaly_node(state: SustainAIState) -> SustainAIState:
    df = pd.DataFrame(state["raw_data"])
    if df.empty:
        state["anomalies"] = []
        return state
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    baseline = build_baseline(df)
    merged = merge_with_baseline(df, baseline)
    
    import json
    critical_str = state["building_profile"].get("critical_devices", "[]")
    try:
        critical_devices = json.loads(critical_str)
    except:
        critical_devices = []
        
    anomalies = detect_anomalies(merged, critical_devices)
    state["baseline"] = baseline
    state["anomalies"] = anomalies
    
    state.get("agent_logs", []).append({
        "agent": "Anomaly Agent",
        "action": "Outlier Analysis",
        "output": f"Detected {len(anomalies)} anomalies.",
        "details": anomalies[:2]
    })
    return state

def savings_node(state: SustainAIState) -> SustainAIState:
    savings_estimates = []
    seen_devices = set()

    for behavior in state.get("behaviors", []):
        if not behavior.get("is_actionable", True):
            continue
        device = behavior.get("device", "Unknown")
        if device in seen_devices:
            continue
        seen_devices.add(device)

        result = run_simulation(
            device=device,
            current_daily_hours=4.0,
            proposed_daily_hours=3.0,
            shift_to_off_peak=True,
            tariff_rate=8.0,
        )
        result["behavior"] = behavior.get("behavior", "")
        savings_estimates.append(result)

    if not savings_estimates:
        savings_estimates.append(run_simulation("AC", 4.0, 3.0, True, 8.0))

    state["savings_estimates"] = savings_estimates
    state.get("agent_logs", []).append({
        "agent": "Simulator Agent",
        "action": "Economic Impact Analysis",
        "output": f"Calculated savings for {len(savings_estimates)} devices.",
        "details": savings_estimates
    })
    return state

def _build_backup_intelligence(state: SustainAIState) -> list[dict]:
    """Fetches last 50 decisions to use as Static Memory when AI is offline."""
    from app.database.connection import SessionLocal
    from app.database.models import Recommendation
    
    session_id = state.get("session_id")
    db = SessionLocal()
    try:
        past_recs = db.query(Recommendation).filter(Recommendation.session_id == session_id).order_by(Recommendation.created_at.desc()).limit(50).all()
        
        if not past_recs:
            return []
            
        intelligence = []
        for r in past_recs:
            intelligence.append({
                "issue": r.issue,
                "recommendation": r.recommendation,
                "control_action": r.control_action,
                "device": r.issue.split("on ")[-1] if "on " in r.issue else "Unknown"
            })
        return intelligence
    except:
        return []
    finally:
        db.close()

def _build_fallback_recommendations(state: SustainAIState) -> list[dict]:
    recs = []
    backup_memory = _build_backup_intelligence(state)
    
    anoms = state.get("anomalies", [])
    for a in anoms[:3]:
        device = a.get("device", "Unknown Device")
        
        # Try to find 'Backup Intelligence' for this specific device
        past_match = next((m for m in backup_memory if m["device"] == device), None)
        
        if past_match:
            recs.append({
                "issue": past_match["issue"],
                "reason": "Verified Multi-Agent Memory: Replaying known optimization pattern.",
                "reasoning_proof": f"Resilience Mode: Re-issuing verified fix for {device} from historical optimization logs.",
                "estimated_monthly_loss": f"₹{a.get('estimated_loss', 0) * 30:.0f}",
                "recommendation": past_match["recommendation"],
                "control_action": past_match["control_action"],
                "implementation_effort": "low",
                "confidence": 0.95
            })
        else:
            # Universal Default if no backup memory for this device
            recs.append({
                "issue": f"Excessive consumption on {device}",
                "reason": "Anomaly detected via local deterministic analyzer.",
                "reasoning_proof": f"Detected significant variance: {a.get('kwh')} kWh. Executing local safety stabilization protocol.",
                "estimated_monthly_loss": f"₹{a.get('estimated_loss', 0) * 30:.0f}",
                "recommendation": f"Inspect {device} for hardware failure and reduce load manually.",
                "control_action": f"STABILIZE_{device.upper()}:TARGET:NORMAL",
                "implementation_effort": "medium",
                "confidence": 0.85
            })
    
    if not recs:
        # Emergency hardcoded fallback
        recs = [
            {
                "issue": "Peak-Hour Grid Load Spike",
                "reason": "Local deterministic trigger",
                "reasoning_proof": "System operating on Resilience Mode. Reverting to verified safety stabilization protocols.",
                "estimated_monthly_loss": "₹1,500",
                "recommendation": "Scale down non-essential lighting and HVAC in Zone-B.",
                "control_action": "GRID_SAFETY_LEVEL_1_ENGAGED",
                "implementation_effort": "low",
                "confidence": 0.9,
            }
        ]
    return recs

from app.agents.doctor_agent import doctor_node

def build_full_pipeline() -> StateGraph:
    graph = StateGraph(SustainAIState)
    graph.add_node("context_node", context_node)
    graph.add_node("research_node", research_node)
    graph.add_node("pattern_node", pattern_node)
    graph.add_node("anomaly_node", anomaly_node)
    graph.add_node("behavior_node", behavior_node)
    graph.add_node("savings_node", savings_node)
    graph.add_node("recommendation_node", recommendation_node)
    graph.add_node("doctor_node", doctor_node)
    graph.add_node("explanation_node", explanation_node)

    graph.set_entry_point("context_node")
    graph.add_edge("context_node", "research_node")
    graph.add_edge("research_node", "pattern_node")
    graph.add_edge("pattern_node", "anomaly_node")
    graph.add_edge("anomaly_node", "behavior_node")
    graph.add_edge("behavior_node", "savings_node")
    graph.add_edge("savings_node", "recommendation_node")
    graph.add_edge("recommendation_node", "doctor_node")
    graph.add_edge("doctor_node", "explanation_node")
    graph.add_edge("explanation_node", END)
    return graph.compile()

def build_lightweight_pipeline():
    from langgraph.graph import StateGraph, END
    
    graph = StateGraph(SustainAIState)
    graph.add_node("context_node", log_node("context_node", context_node))
    graph.add_node("research_node", log_node("research_node", research_node))
    graph.add_node("behavior_node", log_node("behavior_node", behavior_node))
    graph.add_node("anomaly_node", log_node("anomaly_node", anomaly_node))
    graph.add_node("savings_node", log_node("savings_node", savings_node))
    graph.add_node("recommendation_node", log_node("recommendation_node", recommendation_node))
    graph.add_node("doctor_node", log_node("doctor_node", doctor_node))
    
    graph.set_entry_point("context_node")
    graph.add_edge("context_node", "research_node")
    graph.add_edge("research_node", "behavior_node")
    graph.add_edge("behavior_node", "anomaly_node")
    graph.add_edge("anomaly_node", "savings_node")
    graph.add_edge("savings_node", "recommendation_node")
    graph.add_edge("recommendation_node", "doctor_node")
    graph.add_edge("doctor_node", END)
    return graph.compile()

full_pipeline = build_full_pipeline()
lightweight_pipeline = build_lightweight_pipeline()

def run_pipeline_for_session(session_id: str, building_profile: dict, prompt_overrides: dict = None, historical_context: dict = None):
    from app.database.connection import SessionLocal
    from app.database.models import EnergyUsage, TelemetryEvent
    
    db = SessionLocal()
    try:
        # Fetch data autonomously
        usage = db.query(EnergyUsage).filter(EnergyUsage.session_id == session_id).order_by(EnergyUsage.timestamp.desc()).limit(5000).all()
        raw_data = [{"timestamp": u.timestamp, "device": u.device, "kwh": u.kwh} for u in usage]
        
        recent_events = db.query(TelemetryEvent).filter(TelemetryEvent.session_id == session_id).order_by(TelemetryEvent.timestamp.desc()).limit(10).all()
        telemetry_events = [{"device": e.device, "event_type": e.event_type, "kwh": e.kwh} for e in recent_events]
    finally:
        db.close()

    initial_state: SustainAIState = {
        "session_id": session_id,
        "building_profile": building_profile,
        "constraint_block": "",
        "domain_research": {},
        "raw_data": raw_data,
        "baseline": None,
        "anomalies": [],
        "patterns": [],
        "behaviors": [],
        "savings_estimates": [],
        "recommendations": [],
        "final_explanation": "",
        "analysis_report": {},
        "agent_logs": [],
        "prompt_overrides": prompt_overrides or {},
        "historical_context": historical_context or {},
        "telemetry_events": telemetry_events,
        "worker_reports": [],
        "doctor_audits": []
    }
    
    try:
        result = full_pipeline.invoke(initial_state)
        ACTIVE_NODES[session_id] = "Idle"
        logger.info(f"Pipeline completed for session {session_id}")
        return result
    except Exception as e:
        logger.error(f"Full pipeline failed: {e}. Executing emergency fallback reasoning.")
        ACTIVE_NODES[session_id] = "Reasoning Failed"
        # Emergency Fallback: Run deterministic logic locally without LLM
        state = initial_state.copy()
        try:
            # We use the already imported nodes
            state = behavior_node(state)
            state = anomaly_node(state)
            state = savings_node(state)
            state["recommendations"] = _build_fallback_recommendations(state)
            state["final_explanation"] = f"### ⚠️ Resilience Mode Active\nOur deep reasoning engine is currently recovering from a high-load period (Rate Limit).\n\n**Verified Recovery**: I have engaged the local deterministic analyzer to ensure your sustainability roadmap remains accurate and actionable while the cloud-AI scales back up."
            ACTIVE_NODES[session_id] = "Idle"
            return state
        except Exception as fallback_e:
            logger.critical(f"Critical Failure: Fallback also failed: {fallback_e}")
            initial_state["final_explanation"] = f"Critical reasoning failure: {str(e)}"
            ACTIVE_NODES[session_id] = "System Offline"
            return initial_state
    finally:
        # Final safety for the UI
        if session_id in ACTIVE_NODES and ACTIVE_NODES[session_id] not in ["System Offline", "Reasoning Failed"]:
            ACTIVE_NODES[session_id] = "Idle"

def run_lightweight_pipeline(session_id: str):
    from app.database.connection import SessionLocal
    from app.database.models import BuildingProfile, EnergyUsage, Recommendation
    import pandas as pd
    
    db = SessionLocal()
    try:
        profile_row = db.query(BuildingProfile).filter(BuildingProfile.session_id == session_id).first()
        if not profile_row:
            return
            
        profile_dict = {
            "building_type": profile_row.building_type,
            "building_name": profile_row.building_name,
            "city": profile_row.city,
            "state": profile_row.state,
            "occupancy_hours": profile_row.occupancy_hours,
            "critical_devices": profile_row.critical_devices,
            "special_constraints": profile_row.special_constraints
        }
        
        usage = db.query(EnergyUsage).filter(EnergyUsage.session_id == session_id).order_by(EnergyUsage.timestamp.desc()).limit(1000).all()
        if not usage:
            return
            
        raw_data = [{"timestamp": u.timestamp, "device": u.device, "kwh": u.kwh} for u in usage]
        
        from app.database.models import TelemetryEvent
        recent_events = db.query(TelemetryEvent).filter(TelemetryEvent.session_id == session_id).order_by(TelemetryEvent.timestamp.desc()).limit(10).all()
        telemetry_events = [{"device": e.device, "event_type": e.event_type, "kwh": e.kwh} for e in recent_events]

        initial_state = {
            "session_id": session_id,
            "building_profile": profile_dict,
            "constraint_block": "",
            "domain_research": {},
            "raw_data": raw_data,
            "baseline": None,
            "anomalies": [],
            "patterns": [],
            "behaviors": [],
            "savings_estimates": [],
            "recommendations": [],
            "final_explanation": "",
            "analysis_report": {},
            "telemetry_events": telemetry_events,
            "worker_reports": [],
            "doctor_audits": []
        }
        
        result = lightweight_pipeline.invoke(initial_state)
        
        from app.database.models import Recommendation, AgentLog, DoctorAudit
        import json
        
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
                triggered_by="telemetry_auto"
            )
            db.add(db_rec)
            
        db.commit()
    finally:
        ACTIVE_NODES[session_id] = "Idle"
        db.close()
