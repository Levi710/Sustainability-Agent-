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
        
        try:
            new_state = func(state)
            if not isinstance(new_state, dict):
                return new_state
                
            # Check for new logs or audits to stream to DB
            new_logs = new_state.get("agent_logs", [])
            new_audits = new_state.get("doctor_audits", [])
            
            if new_logs or new_audits:
                from app.database.connection import SessionLocal
                from app.database.models import AgentLog, DoctorAudit
                import json
                db = SessionLocal()
                try:
                    # Stream Logs
                    for log in new_logs:
                        db_log = AgentLog(
                            session_id=session_id,
                            agent_name=log.get("agent", ""),
                            device=log.get("device"),
                            action=log.get("action", ""),
                            output=log.get("output", ""),
                            details=json.dumps(log.get("details", {}), default=str)
                        )
                        db.add(db_log)
                        
                    # Stream Audits
                    for audit in new_audits:
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

def merge_update_node(session_id: str, db: Any, state: dict, node_name: str, node_func: Any):
    ACTIVE_NODES[session_id] = node_name
    logger.info(f"Fallback Node starting: {node_name}")
    try:
        update = node_func(state)
        if isinstance(update, dict):
            for k, v in update.items():
                if k == "agent_logs" and k in state:
                    state[k] = state[k] + v
                elif k == "doctor_audits" and k in state:
                    state[k] = state[k] + v
                else:
                    state[k] = v
            
            # Stream new logs instantly
            new_logs = update.get("agent_logs", [])
            new_audits = update.get("doctor_audits", [])
            
            from app.database.models import AgentLog, DoctorAudit
            import json
            
            for log in new_logs:
                db_log = AgentLog(
                    session_id=session_id,
                    agent_name=log.get("agent", ""),
                    device=log.get("device"),
                    action=log.get("action", ""),
                    output=log.get("output", ""),
                    details=json.dumps(log.get("details", {}), default=str)
                )
                db.add(db_log)
            for audit in new_audits:
                db_audit = DoctorAudit(
                    session_id=session_id,
                    device=audit.get("device", ""),
                    verification_status=audit.get("verification_status", ""),
                    doctor_notes=audit.get("doctor_notes", "")
                )
                db.add(db_audit)
            db.commit()
    except Exception as e:
        logger.error(f"Fallback Node {node_name} failed: {e}")

from typing import Annotated, Union
import operator

class SustainAIState(TypedDict):
    session_id: str
    building_profile: dict
    constraint_block: str
    domain_research: dict
    raw_data: list[dict]
    baseline: Any
    anomalies: Annotated[list[dict], operator.add]
    patterns: Annotated[list[dict], operator.add]
    behaviors: Annotated[list[dict], operator.add]
    savings_estimates: Annotated[list[dict], operator.add]
    recommendations: Annotated[list[dict], operator.add]
    final_explanation: str
    analysis_report: dict
    agent_logs: Annotated[list[dict], operator.add]
    prompt_overrides: dict
    historical_context: dict
    telemetry_events: list[dict]
    worker_reports: list[dict]
    doctor_audits: Annotated[list[dict], operator.add]

def _get_api_key():
    # Priority: Groq then NVIDIA
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and groq_key != "your_key_here":
        return ("groq", groq_key)
        
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_key and nvidia_key != "your_key_here":
        return ("nvidia", nvidia_key)
        
    return None

def _raw_llm_call(provider_info: tuple, system_prompt: str, user_content: str) -> str:
    provider, api_key = provider_info
    
    if provider == "local":
        invoke_url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/api/chat")
        model = os.getenv("LOCAL_MODEL", "llama3.2")
    elif provider == "groq":
        invoke_url = "https://api.groq.com/openai/v1/chat/completions"
        model = "llama-3.3-70b-versatile"
    else:
        # NVIDIA NIM API
        invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        model = "meta/llama-3.1-70b-instruct"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2,
        "max_tokens": 4096,
        "stream": False
    }
    
    import time
    max_retries = 1
    last_error = None
    for i in range(max_retries):
        try:
            logger.info("LLM provider %s invoked with model %s", provider, model)
            
            response = requests.post(invoke_url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("LLM provider %s succeeded", provider)
            else:
                logger.warning("LLM provider %s failed with HTTP %s", provider, response.status_code)

            if response.status_code in [401, 403, 404] and provider != "local":
                raise Exception(f"{provider.capitalize()} API key invalid or model unavailable ({response.status_code})")

            if response.status_code == 429:
                raise Exception(f"{provider.capitalize()} rate limited ({response.status_code})")
            
            res_json = response.json()
            if "choices" in res_json:
                content = res_json["choices"][0]["message"]["content"]
            elif "message" in res_json:
                content = res_json["message"]["content"]
            else:
                content = str(res_json)
            
            # Clean up markdown
            content = re.sub(r'^```(?:json)?', '', content).strip()
            content = re.sub(r'```$', '', content).strip()
            return content
        except Exception as e:
            last_error = e
            if i == max_retries - 1:
                raise e
            time.sleep(1)
    
    # All retries exhausted (e.g. all 429s) — raise so caller can try fallback
    if last_error:
        raise last_error
    return ""

def _llm_call(system_prompt: str, user_content: str, fallback: Any) -> Any:
    local_enabled = os.getenv("USE_LOCAL_LLM", "False").lower() == "true"
    
    providers = []
    if local_enabled:
        ollama_key = os.getenv("OLLAMA_API_KEY", "no_key")
        providers.append(("local", ollama_key))
        
    # Try Groq first
    groq_key = os.getenv("GROQ_API_KEY")
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    
    # Try NVIDIA first if Groq is limited
    if nvidia_key and nvidia_key != "your_key_here":
        providers.append(("nvidia", nvidia_key))
    if groq_key and groq_key != "your_key_here":
        providers.append(("groq", groq_key))
    
    if not providers:
        logger.warning("No API Key found, using fallback")
        return fallback
    
    for provider_info in providers:
        try:
            content = _raw_llm_call(provider_info, system_prompt, user_content)
            return json.loads(content)
        except Exception as e:
            logger.warning(f"LLM call failed with {provider_info[0]}: {e}")
            continue
    
    logger.error("All LLM providers failed, using fallback")
    return fallback

def pattern_node(state: SustainAIState) -> SustainAIState:
    df = pd.DataFrame(state["raw_data"])
    if df.empty:
        return {"patterns": []}
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], format='%Y-%m-%d %H:%M:%S.%f')
    except Exception:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
    
    import json
    critical_str = state["building_profile"].get("critical_devices", "[]")
    try:
        critical_devices = json.loads(critical_str)
    except:
        critical_devices = []
        
    patterns = detect_habit_patterns(df, critical_devices)
    
    return {
        "patterns": patterns,
        "agent_logs": [{
            "agent": "Behavior Agent",
            "action": "Pattern Detection",
            "output": f"Detected {len(patterns)} habit patterns.",
            "details": patterns[:2]
        }]
    }

def surveillance_node(state: SustainAIState) -> SustainAIState:
    df = pd.DataFrame(state["raw_data"])
    if df.empty:
        return {"anomalies": []}
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], format='%Y-%m-%d %H:%M:%S.%f')
    except Exception:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
    baseline = build_baseline(df)
    merged = merge_with_baseline(df, baseline)
    
    import json
    critical_str = state["building_profile"].get("critical_devices", "[]")
    try:
        critical_devices = json.loads(critical_str)
    except:
        critical_devices = []
        
    anomalies = detect_anomalies(merged, critical_devices)
    
    # Compile a detailed dispatch report for downstream fixing agents
    details_report = f"Fleet Surveillance poll completed. Checked {len(df['device'].unique()) if 'device' in df.columns else 0} registered devices. "
    if anomalies:
        details_report += f"Found {len(anomalies)} anomalous spikes/offline events. Dispatching target instructions to Recommendation Agent to resolve."
    else:
        details_report += "All devices operating within baseline thresholds. System Status: OPTIMAL."
        
    return {
        "baseline": baseline,
        "anomalies": anomalies,
        "agent_logs": [{
            "agent": "Surveillance Agent",
            "action": "IoT Fleet Surveillance snapshot",
            "output": details_report,
            "details": anomalies[:2]
        }]
    }

def savings_node(state: SustainAIState) -> SustainAIState:
    try:
        from rag.retriever import retriever
    except ModuleNotFoundError:
        from backend.rag.retriever import retriever

    savings_estimates = []
    seen_devices = set()

    for behavior in state.get("behaviors", []):
        if not behavior.get("is_actionable", True):
            continue
        device = behavior.get("device", "Unknown")
        if device in seen_devices:
            continue
        seen_devices.add(device)

        # Query local RAG specs dynamically matching the device type
        spec = retriever.retrieve_by_device(device)

        result = run_simulation(
            device=device,
            current_daily_hours=spec.get("typical_daily_hours", 4.0),
            proposed_daily_hours=spec.get("proposed_daily_hours", 3.0),
            shift_to_off_peak=True,
            tariff_rate=8.0,
            kwh_per_hour=spec.get("rated_kw", 1.5)
        )
        result["behavior"] = behavior.get("behavior", "")
        result["spec_source"] = spec.get("source", "BEE Star Rating Guideline")
        result["section"] = spec.get("section", "Standard Guidelines")
        result["page"] = spec.get("page", 1)

        savings_estimates.append(result)

    if not savings_estimates:
        spec = retriever.retrieve_by_device("AC")
        fallback_res = run_simulation(
            device="AC",
            current_daily_hours=spec.get("typical_daily_hours", 4.0),
            proposed_daily_hours=spec.get("proposed_daily_hours", 3.0),
            shift_to_off_peak=True,
            tariff_rate=8.0,
            kwh_per_hour=spec.get("rated_kw", 1.5)
        )
        fallback_res["spec_source"] = spec.get("source", "BEE Star Rating Guideline")
        fallback_res["section"] = spec.get("section", "Standard Guidelines")
        fallback_res["page"] = spec.get("page", 1)
        savings_estimates.append(fallback_res)

    return {
        "savings_estimates": savings_estimates,
        "agent_logs": [{
            "agent": "Simulator Agent",
            "action": "Economic Impact Analysis",
            "output": f"Calculated grounded savings for {len(savings_estimates)} devices.",
            "details": savings_estimates
        }]
    }

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
    seen_devices = set()
    
    anoms = state.get("anomalies", [])
    for a in anoms[:10]:  # Check more anomalies but de-dup by device
        device = a.get("device", "Unknown Device")
        if device in seen_devices:
            continue
        seen_devices.add(device)
        if len(recs) >= 3:
            break
        
        # Try to find 'Backup Intelligence' for this specific device
        past_match = next((m for m in backup_memory if m["device"] == device), None)
        
        if past_match:
            recs.append({
                "issue": past_match["issue"],
                "device": device,
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
                "device": device,
                "reason": "Anomaly detected via local deterministic analyzer.",
                "reasoning_proof": f"Detected significant variance: {a.get('kwh')} kWh. Executing local safety stabilization protocol.",
                "estimated_monthly_loss": f"₹{a.get('estimated_loss', 0) * 30:.0f}",
                "recommendation": f"Inspect {device} for hardware failure and reduce load manually.",
                "control_action": f"STABILIZE_{device.upper()}:TARGET:NORMAL",
                "implementation_effort": "medium",
                "confidence": 0.85
            })
    
    if not recs:
        telemetry_events = state.get("telemetry_events", [])
        actionable_events = [
            e for e in telemetry_events
            if e.get("event_type") not in [None, "normal"] and e.get("device")
        ]
        for event in actionable_events[:3]:
            device = event.get("device", "Unknown_Device")
            event_type = event.get("event_type", "telemetry_event")
            recs.append({
                "issue": f"Telemetry surveillance event on {device}",
                "device": device,
                "reason": f"Surveillance Agent reported {event_type}; device requires automated stabilization or manual inspection.",
                "reasoning_proof": f"Latest telemetry event for {device}: {event_type}, reading {event.get('kwh', 'N/A')} kWh.",
                "estimated_monthly_loss": "₹1,500",
                "recommendation": f"Inspect {device} and apply the safest non-critical stabilization command.",
                "control_action": f"INSPECT:{device}",
                "implementation_effort": "medium",
                "confidence": 0.82,
            })

    if not recs:
        # Emergency hardcoded fallback
        recs = [
            {
                "issue": "Peak-Hour Grid Load Spike",
                "device": "General",
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
    graph.add_node("context_node", log_node("context_node", context_node))
    graph.add_node("research_node", log_node("research_node", research_node))
    graph.add_node("pattern_node", log_node("pattern_node", pattern_node))
    graph.add_node("surveillance_node", log_node("surveillance_node", surveillance_node))
    graph.add_node("behavior_node", log_node("behavior_node", behavior_node))
    graph.add_node("savings_node", log_node("savings_node", savings_node))
    graph.add_node("recommendation_node", log_node("recommendation_node", recommendation_node))
    graph.add_node("doctor_node", log_node("doctor_node", doctor_node))
    graph.add_node("explanation_node", log_node("explanation_node", explanation_node))

    graph.set_entry_point("context_node")
    graph.add_edge("context_node", "research_node")
    graph.add_edge("context_node", "surveillance_node")
    graph.add_edge("context_node", "pattern_node")
    
    graph.add_edge("research_node", "behavior_node")
    graph.add_edge("surveillance_node", "behavior_node")
    graph.add_edge("pattern_node", "behavior_node")
    
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
    graph.add_node("pattern_node", log_node("pattern_node", pattern_node))
    graph.add_node("surveillance_node", log_node("surveillance_node", surveillance_node))
    graph.add_node("behavior_node", log_node("behavior_node", behavior_node))
    graph.add_node("savings_node", log_node("savings_node", savings_node))
    graph.add_node("recommendation_node", log_node("recommendation_node", recommendation_node))
    graph.add_node("doctor_node", log_node("doctor_node", doctor_node))
    graph.add_node("explanation_node", log_node("explanation_node", explanation_node))
    
    graph.set_entry_point("context_node")
    graph.add_edge("context_node", "research_node")
    graph.add_edge("context_node", "surveillance_node")
    graph.add_edge("context_node", "pattern_node")
    
    graph.add_edge("research_node", "behavior_node")
    graph.add_edge("surveillance_node", "behavior_node")
    graph.add_edge("pattern_node", "behavior_node")
    
    graph.add_edge("behavior_node", "savings_node")
    graph.add_edge("savings_node", "recommendation_node")
    graph.add_edge("recommendation_node", "doctor_node")
    graph.add_edge("doctor_node", "explanation_node")
    graph.add_edge("explanation_node", END)
    return graph.compile()

full_pipeline = build_full_pipeline()
lightweight_pipeline = build_lightweight_pipeline()

def run_pipeline_for_session(session_id: str, building_profile: dict, prompt_overrides: dict = None, historical_context: dict = None):
    from app.database.connection import SessionLocal
    from app.database.models import EnergyUsage, TelemetryEvent, AgentLog, DoctorAudit
    
    db = SessionLocal()
    try:
        # Clear previous agent logs and audits for this session to prevent duplicates
        try:
            db.query(AgentLog).filter(AgentLog.session_id == session_id).delete()
            db.query(DoctorAudit).filter(DoctorAudit.session_id == session_id).delete()
            db.commit()
        except Exception as clear_e:
            logger.warning(f"Failed to clear old logs: {clear_e}")
            db.rollback()

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
        from app.database.connection import SessionLocal
        fallback_db = SessionLocal()
        try:
            # Force Context Agent log first
            ACTIVE_NODES[session_id] = "context_node"
            
            merge_update_node(session_id, fallback_db, state, "surveillance_node", surveillance_node)
            merge_update_node(session_id, fallback_db, state, "pattern_node", pattern_node)
            merge_update_node(session_id, fallback_db, state, "behavior_node", behavior_node)
            merge_update_node(session_id, fallback_db, state, "savings_node", savings_node)
            
            # Recommendations Fallback
            ACTIVE_NODES[session_id] = "recommendation_node"
            state["recommendations"] = _build_fallback_recommendations(state)
            
            # Doctor Fallback
            merge_update_node(session_id, fallback_db, state, "doctor_node", doctor_node)
            
            # Explanation Fallback
            merge_update_node(session_id, fallback_db, state, "explanation_node", explanation_node)
            
            ACTIVE_NODES[session_id] = "Idle"
            return state
        except Exception as fallback_e:
            logger.critical(f"Critical Failure: Fallback also failed: {fallback_e}")
            initial_state["final_explanation"] = f"Critical reasoning failure: {str(e)}"
            ACTIVE_NODES[session_id] = "System Offline"
            return initial_state
        finally:
            fallback_db.close()
    finally:
        # Final safety for the UI
        if session_id in ACTIVE_NODES and ACTIVE_NODES[session_id] not in ["System Offline", "Reasoning Failed"]:
            ACTIVE_NODES[session_id] = "Idle"

def run_lightweight_pipeline(session_id: str):
    from app.database.connection import SessionLocal
    from app.database.models import BuildingProfile, EnergyUsage, Recommendation, AgentLog, DoctorAudit
    import pandas as pd
    
    db = SessionLocal()
    try:
        # Clear previous agent logs and audits for this session to prevent duplicates
        try:
            db.query(AgentLog).filter(AgentLog.session_id == session_id).delete()
            db.query(DoctorAudit).filter(DoctorAudit.session_id == session_id).delete()
            db.commit()
        except Exception as clear_e:
            logger.warning(f"Failed to clear old logs: {clear_e}")
            db.rollback()
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
            "agent_logs": [],
            "prompt_overrides": {},
            "historical_context": {},
            "telemetry_events": telemetry_events,
            "worker_reports": [],
            "doctor_audits": []
        }
        
        ACTIVE_NODES[session_id] = "Auto-Analyzing"
        try:
            result = lightweight_pipeline.invoke(initial_state)
            logger.info(f"Lightweight pipeline completed for session {session_id}")
        except Exception as e:
            logger.error(f"Lightweight pipeline invoke failed for {session_id}: {e}")
            # Fallback: run deterministic analysis
            try:
                # Force Context Agent log first
                ACTIVE_NODES[session_id] = "context_node"
                
                merge_update_node(session_id, db, initial_state, "surveillance_node", surveillance_node)
                merge_update_node(session_id, db, initial_state, "pattern_node", pattern_node)
                merge_update_node(session_id, db, initial_state, "behavior_node", behavior_node)
                merge_update_node(session_id, db, initial_state, "savings_node", savings_node)
                
                # Recommendations Fallback
                ACTIVE_NODES[session_id] = "recommendation_node"
                initial_state["recommendations"] = _build_fallback_recommendations(initial_state)
                
                # Doctor Fallback
                merge_update_node(session_id, db, initial_state, "doctor_node", doctor_node)
                
                # Explanation Fallback
                merge_update_node(session_id, db, initial_state, "explanation_node", explanation_node)
                result = initial_state
            except Exception as fallback_e:
                logger.error(f"Lightweight fallback also failed: {fallback_e}")
                return

        
        from app.database.models import Recommendation, AgentLog, DoctorAudit, SessionReport
        import json
        
        # Save and Dispatch recommendations
        from app.services.iot_dispatcher import IoTCommandDispatcher, log_control_signal
        
        for rec in result.get("recommendations", []):
            control_action = rec.get("control_action", "")
            
            # 1. Save to Database
            db_rec = Recommendation(
                session_id=session_id,
                issue=rec.get("issue", ""),
                reason=rec.get("reason", ""),
                reasoning_proof=rec.get("reasoning_proof", ""),
                control_action=control_action,
                estimated_monthly_loss=rec.get("estimated_monthly_loss", ""),
                recommendation=rec.get("recommendation", ""),
                projected_savings=0.0,
                confidence=rec.get("confidence", 0.9),
                triggered_by="telemetry_auto"
            )
            db.add(db_rec)
            
            # 2. Dispatch to Machine Bridge if a control action exists
            if control_action:
                from app.services.config import settings
                auto_fix_enabled = settings.auto_fix
                
                # Extract device ID from issue or details (heuristic for demo)
                device_id = rec.get("device") or (
                    rec.get("issue", "").split("on ")[-1] if "on " in rec.get("issue", "") else "General"
                )
                
                if auto_fix_enabled:
                    dispatch_result = IoTCommandDispatcher.dispatch(device_id, control_action)
                    log_control_signal(session_id, device_id, control_action, dispatch_result)
                else:
                    # Log skip for comparison purposes
                    logger.info(f"COMPARISON_MODE: [SKIP_FIX] {device_id} -> {control_action}")
                    log_control_signal(session_id, device_id, f"[MONITOR_ONLY] {control_action}", {"status": "SKIPPED_FOR_COMPARISON"})
        
        # Save traces defensively. The wrapper streams these live, but background
        # execution should still leave a complete audit trail if a stream write is skipped.
        for log in result.get("agent_logs", []):
            exists = db.query(AgentLog).filter(
                AgentLog.session_id == session_id,
                AgentLog.agent_name == log.get("agent", ""),
                AgentLog.action == log.get("action", ""),
                AgentLog.output == log.get("output", ""),
            ).first()
            if not exists:
                db.add(AgentLog(
                    session_id=session_id,
                    agent_name=log.get("agent", ""),
                    device=log.get("device"),
                    action=log.get("action", ""),
                    output=log.get("output", ""),
                    details=json.dumps(log.get("details", {}), default=str),
                ))

        for audit in result.get("doctor_audits", []):
            exists = db.query(DoctorAudit).filter(
                DoctorAudit.session_id == session_id,
                DoctorAudit.device == audit.get("device", ""),
                DoctorAudit.verification_status == audit.get("verification_status", ""),
                DoctorAudit.doctor_notes == audit.get("doctor_notes", ""),
            ).first()
            if not exists:
                db.add(DoctorAudit(
                    session_id=session_id,
                    device=audit.get("device", ""),
                    verification_status=audit.get("verification_status", ""),
                    doctor_notes=audit.get("doctor_notes", ""),
                ))

        report = result.get("analysis_report", {}) or {}
        final_explanation = result.get("final_explanation") or report.get("final_explanation") or ""
        if final_explanation or report:
            db.add(SessionReport(
                session_id=session_id,
                final_explanation=final_explanation,
                summary_json=json.dumps(report, default=str),
            ))
            
        db.commit()
        logger.info(f"Saved {len(result.get('recommendations', []))} auto-recommendations for session {session_id}")
    except Exception as e:
        logger.error(f"Lightweight pipeline critical error for {session_id}: {e}")
    finally:
        ACTIVE_NODES[session_id] = "Idle"
        db.close()
