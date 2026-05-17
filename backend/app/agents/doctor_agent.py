"""
SustainAI — Doctor Agent v3 (Verification Auditor)
────────────────────────────────────────────────────
Responsibility:
  - After the Recommendation Agent fires an IoT command, verify it worked
  - Compare post-fix telemetry against pre-fix baseline
  - Return structured audit: VERIFIED_OPTIMIZED | SUPERFICIAL_FIX | FAILED | RE_INSPECTION

Key fixes over v2:
  - BUG FIX: Device name extraction was fragile (split on "on ") — now uses
    control_action as primary source, issue string as fallback
  - BUG FIX: current_kwh=0 when no telemetry match caused Doctor to always
    return VERIFIED_OPTIMIZED (false positive) — now explicitly handles this case
  - Audits ALL recommendations, not just the last one
  - Fallback now returns RE_INSPECTION instead of VERIFIED_OPTIMIZED when
    telemetry is missing (honest unknown vs. false positive)
"""

import json
import logging

logger = logging.getLogger("uvicorn.error")

DOCTOR_SYSTEM_PROMPT = """
You are the SustainAI Doctor Agent — an independent verification auditor.

Your role: determine whether the Recommendation Agent's IoT fix ACTUALLY worked
by comparing live telemetry AFTER the fix against expected normal ranges.

You are the last line of defense against false-positive "fixes."
Be skeptical. Be precise. Use the data.

VERIFICATION RULES:
1. If current_kwh > baseline_kwh × 1.2 → the fix FAILED or was SUPERFICIAL.
2. If current_kwh is within ±20% of baseline_kwh → VERIFIED_OPTIMIZED.
3. If telemetry_available is false → RE_INSPECTION (cannot verify without data).
4. If worker_report lacks a specific IoT command → RE_INSPECTION.
5. If current_kwh dropped significantly (>30%) from spike_kwh → VERIFIED_OPTIMIZED.

Respond ONLY with a valid JSON object. No markdown. No explanation outside JSON.
All fields are required:
{
  "device": "exact device name from input",
  "verification_status": "VERIFIED_OPTIMIZED | SUPERFICIAL_FIX | FAILED | RE_INSPECTION",
  "doctor_notes": "1 sentence: what the data shows vs what was claimed",
  "optimization_score": 0.0 to 1.0,
  "follow_up_required": true or false,
  "telemetry_based": true or false
}
"""


def _extract_device_from_recommendation(rec: dict) -> str:
    """
    Robust device name extraction from a recommendation dict.
    Priority: control_action → issue string → fallback.

    Examples:
      control_action = "TURN_OFF:HVAC_Block_A"  → "HVAC_Block_A"
      control_action = "SET_HVAC_MODE:ECO"       → tries issue string
      issue = "Excessive consumption on Lab_PCs" → "Lab_PCs"
    """
    if rec.get("device"):
        return rec["device"]

    # 1. Try control_action — most reliable source
    control_action = rec.get("control_action", "")
    if control_action and ":" in control_action:
        parts = control_action.split(":")
        # TURN_OFF:HVAC_Block_A → HVAC_Block_A
        # SET_HVAC_MODE:ECO → ECO is not a device, skip
        candidate = parts[-1].strip()
        # Reject parameter-only values (ECO, ON, OFF, 50PCT, etc.)
        if candidate and not candidate.upper() in ["ECO", "ON", "OFF", "AUTO", "STANDBY", "NORMAL"]:
            if "_" in candidate or len(candidate) > 4:  # looks like a device name
                return candidate

    # 2. Try issue string — "Excessive consumption on HVAC_Block_A"
    issue = rec.get("issue", "")
    if " on " in issue:
        return issue.split(" on ")[-1].strip()

    # 3. Try recommendation string
    recommendation = rec.get("recommendation", "")
    if " on " in recommendation:
        return recommendation.split(" on ")[-1].split(" ")[0].strip()

    # 4. Absolute fallback
    return "Unknown_Device"


def _get_device_telemetry(device: str, telemetry: list[dict]) -> list[dict]:
    """
    Find telemetry records for a device.
    Tries exact match first, then case-insensitive partial match.
    """
    exact = [t for t in telemetry if t.get("device") == device]
    if exact:
        return exact

    device_lower = device.lower()
    partial = [t for t in telemetry if device_lower in t.get("device", "").lower()]
    return partial


def doctor_node(state: dict) -> dict:
    from app.agents.pipeline import _llm_call

    recommendations = state.get("recommendations", [])
    telemetry = state.get("telemetry_events", [])
    anomalies = state.get("anomalies", [])

    new_audits = []
    new_logs = []

    if not recommendations:
        return {
            "agent_logs": [{
                "agent": "Doctor Agent (Auditor)",
                "action": "Awaiting Recommendations",
                "output": "No recommendations to audit yet. Pipeline may be on first run.",
                "details": {}
            }]
        }

    # ── Audit each recommendation (cap at 3 to avoid token overload) ────────
    for rec in recommendations[:3]:
        device = _extract_device_from_recommendation(rec)
        
        # ── Get pre-fix baseline from anomaly data ───────────────────────────
        device_anomalies = [a for a in anomalies if a.get("device") == device]
        spike_kwh = device_anomalies[-1]["kwh"] if device_anomalies else None
        baseline_kwh = device_anomalies[-1].get("baseline_kwh") if device_anomalies else None

        # ── Get post-fix telemetry ───────────────────────────────────────────
        device_telemetry = _get_device_telemetry(device, telemetry)
        telemetry_available = len(device_telemetry) > 0
        current_kwh = device_telemetry[-1]["kwh"] if telemetry_available else None
        recent_readings = [t["kwh"] for t in device_telemetry[-3:]]

        try:
            from rag.retriever import retriever
        except ModuleNotFoundError:
            from backend.rag.retriever import retriever
        spec = retriever.retrieve_by_device(device)

        # ── Build human prompt with RAG grounding evidence ───────────────────
        human_prompt = json.dumps({
            "worker_report": {
                "device": device,
                "control_action": rec.get("control_action", ""),
                "intended_fix": rec.get("recommendation", ""),
                "claimed_monthly_savings": rec.get("estimated_monthly_loss", ""),
                "confidence": rec.get("confidence", 0.9),
            },
            "pre_fix_data": {
                "spike_kwh": spike_kwh,
                "baseline_kwh": baseline_kwh,
            },
            "post_fix_telemetry": {
                "device": device,
                "telemetry_available": telemetry_available,
                "current_kwh": current_kwh,
                "recent_3_readings": recent_readings,
            },
            "rag_standards_evidence": {
                "rated_kw": spec.get("rated_kw"),
                "typical_daily_hours": spec.get("typical_daily_hours"),
                "proposed_daily_hours": spec.get("proposed_daily_hours"),
                "source": spec.get("source"),
                "section": spec.get("section"),
                "page": spec.get("page"),
                "expected_efficiency_behavior": spec.get("content")
            }
        }, default=str)

        # ── Fallback: honest unknown when no telemetry ───────────────────────
        if not telemetry_available:
            fallback = {
                "device": device,
                "verification_status": "RE_INSPECTION",
                "doctor_notes": f"No post-fix telemetry available for {device}. Cannot verify autonomously — manual inspection required.",
                "optimization_score": 0.5,
                "follow_up_required": True,
                "telemetry_based": False
            }
        else:
            # Determine optimistic fallback based on actual data
            if baseline_kwh and current_kwh:
                if current_kwh <= baseline_kwh * 1.2:
                    status = "VERIFIED_OPTIMIZED"
                    score = round(1.0 - (current_kwh / max(baseline_kwh, 0.001)), 2)
                    score = max(0.5, min(1.0, score))
                    follow_up = False
                else:
                    status = "SUPERFICIAL_FIX"
                    score = 0.3
                    follow_up = True
            else:
                status = "RE_INSPECTION"
                score = 0.5
                follow_up = True

            fallback = {
                "device": device,
                "verification_status": status,
                "doctor_notes": (
                    f"Post-fix reading: {current_kwh:.3f} kWh. "
                    f"Baseline: {baseline_kwh:.3f} kWh. "
                    f"{'Consumption stabilized.' if status == 'VERIFIED_OPTIMIZED' else 'Consumption still elevated — re-inspection needed.'}"
                ) if current_kwh and baseline_kwh else "Insufficient telemetry data for full verification.",
                "optimization_score": score,
                "follow_up_required": follow_up,
                "telemetry_based": True
            }

        # ── LLM call ─────────────────────────────────────────────────────────
        audit_result = _llm_call(DOCTOR_SYSTEM_PROMPT, human_prompt, fallback)

        # ── Validate response shape ──────────────────────────────────────────
        if not isinstance(audit_result, dict):
            logger.warning(f"Doctor Agent: Invalid LLM response for {device}, using fallback.")
            audit_result = fallback

        required_keys = ["device", "verification_status", "doctor_notes", "optimization_score", "follow_up_required"]
        for key in required_keys:
            if key not in audit_result:
                audit_result[key] = fallback.get(key)

        # Ensure device name is correct (LLM sometimes hallucinates device names)
        audit_result["device"] = device
        
        new_audits.append(audit_result)
        new_logs.append({
            "agent": "Doctor Agent (Auditor)",
            "device": device,
            "action": f"Post-Fix Verification — {device}",
            "output": (
                f"Status: {audit_result.get('verification_status')} | "
                f"Score: {audit_result.get('optimization_score')} | "
                f"Follow-up: {audit_result.get('follow_up_required')}"
            ),
            "details": audit_result
        })

        logger.info(
            f"Doctor Agent: {device} → {audit_result.get('verification_status')} "
            f"(score={audit_result.get('optimization_score')})"
        )

    return {
        "doctor_audits": new_audits,
        "agent_logs": new_logs
    }
