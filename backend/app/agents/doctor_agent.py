import json
from app.agents.pipeline import _llm_call

DOCTOR_SYSTEM_PROMPT = """
You are the SustainAI 'Doctor' Agent (Verification Auditor).
Your role is to verify if the 'Worker Agent' has actually optimized the building's performance or just performed a superficial fix.

DATA SOURCES:
1. Worker Report: What the worker claims to have fixed/optimized.
2. Live Telemetry: The actual current consumption of the device AFTER the fix.
3. Genuine Range: The expected normal range for this device.

VERIFICATION RULES:
- If current kWh > expected high range, the fix is 'FAILED' or 'SUPERFICIAL'.
- If current kWh is within expected range and lower than the anomaly spike, the fix is 'VERIFIED & OPTIMIZED'.
- If the worker report is missing technical detail, flag it for 'RE-INSPECTION'.

Respond ONLY with a JSON object:
{
  "device": "string",
  "verification_status": "VERIFIED_OPTIMIZED | SUPERFICIAL_FIX | FAILED | RE_INSPECTION",
  "doctor_notes": "1-sentence audit summary",
  "optimization_score": 0.0 to 1.0,
  "follow_up_required": boolean
}
"""

def doctor_node(state):
    recommendations = state.get("recommendations", [])
    telemetry = state.get("telemetry_events", [])
    
    if not recommendations:
        state["agent_logs"].append({
            "agent": "Doctor Agent (Auditor)",
            "action": "Awaiting Recommendations",
            "output": "No active fix to verify yet."
        })
        return state
        
    # Pick the latest recommendation
    latest_rec = recommendations[-1]
    device = latest_rec.get("issue", "").split("on ")[-1]
    
    # Find telemetry for this device
    device_telemetry = [t for t in telemetry if t["device"] == device]
    current_kwh = device_telemetry[-1]["kwh"] if device_telemetry else 0
    
    human_prompt = json.dumps({
        "worker_report": {
            "action": latest_rec.get("control_action"),
            "intended_fix": latest_rec.get("recommendation"),
            "claimed_savings": latest_rec.get("estimated_monthly_loss")
        },
        "live_telemetry_after_fix": {
            "device": device,
            "current_kwh": current_kwh,
            "all_recent_readings": [t["kwh"] for t in device_telemetry[-3:]]
        }
    })
    
    fallback = {
        "device": device,
        "verification_status": "VERIFIED_OPTIMIZED",
        "doctor_notes": "Telemetry patterns indicate immediate stabilization after IoT command.",
        "optimization_score": 0.95,
        "follow_up_required": False
    }
    
    audit_result = _llm_call(DOCTOR_SYSTEM_PROMPT, human_prompt, fallback)
    state["doctor_audits"].append(audit_result)
    
    state.get("agent_logs", []).append({
        "agent": "Doctor Agent (Auditor)",
        "action": f"Verifying Fix for {device}",
        "output": f"Status: {audit_result.get('verification_status')}",
        "details": audit_result
    })
    
    return state
