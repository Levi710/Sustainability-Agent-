"""
SustainAI — Recommendation Agent v3
─────────────────────────────────────
Responsibility:
  - Take actionable behaviors + savings estimates + live telemetry events
  - Generate exactly 3 IoT-ready control recommendations
  - Each recommendation must have: time window, INR/month impact, IoT command string
  - Respect constraint_block: critical devices are never recommended for action

Key fixes over v2:
  - Numbered list jump (1→15→16) fixed — rules are now sequential
  - control_action format is now validated and normalized
  - Fallback uses _build_fallback_recommendations properly
  - Historical context deduplication logic is clearer
"""

import json
import logging

logger = logging.getLogger("uvicorn.error")

RECOMMENDATION_SYSTEM = """
You are a certified sustainability advisor for {building_type} buildings in India.

{constraint_block}

DOMAIN RESEARCH:
{domain_research}

TASK: Generate EXACTLY 3 actionable energy optimization recommendations.

MANDATORY RULES (all must be followed):
1. NEVER recommend action on any device listed in CRITICAL DEVICES above.
2. Every recommendation must reference a specific time window (e.g. "between 11PM and 6AM weekdays").
3. Every recommendation must quantify financial impact in INR/month.
4. Every recommendation must be realistic for this building's occupancy pattern.
5. If a VOICE_COMMAND_DETECTED or MOTION_IN_EMPTY_ZONE telemetry event exists, include an immediate automation response for that device.
6. If total load is high across all devices, include a Load Shedding command for non-critical inductive loads.
7. Reference BEE/ECBC/ASHRAE benchmarks where applicable.
8. Do NOT repeat recommendations from HISTORICAL CONTEXT unless the issue is recurring and unresolved.
9. reasoning_proof must contain actual kWh numbers from the behavior/anomaly data.
10. control_action format must be: VERB_DEVICE:PARAMETER (e.g. SET_HVAC_MODE:ECO, TURN_OFF:LAB_PCS, REDUCE_LOAD:LIGHTING_ZONE_B:50PCT)

Respond ONLY with a valid JSON array of exactly 3 objects. No markdown. No explanation outside JSON.
Each object must have ALL of these fields:
{{
  "issue": "One-line description of the problem including device name",
  "reason": "Why this is wasteful for this building type",
  "reasoning_proof": "Specific kWh values: e.g. 'Detected 4.2 kWh spike at 2AM vs 0.5 kWh baseline (Z=3.8)'",
  "recommendation": "Specific human-readable action to take with time window",
  "control_action": "IoT command string: VERB_DEVICE:PARAMETER",
  "estimated_monthly_loss": "₹X,XXX/month",
  "implementation_effort": "low | medium | high",
  "confidence": 0.0 to 1.0
}}
"""


def _normalize_control_action(action: str, device: str) -> str:
    """
    Ensures control_action follows VERB_DEVICE:PARAMETER format.
    Fixes malformed LLM outputs before they reach the IoT dispatcher.
    """
    if not action:
        return f"INSPECT:{device.upper().replace(' ', '_')}"
    # Already valid format
    if ":" in action:
        return action.upper().replace(" ", "_")
    # LLM returned plain text like "Turn off HVAC Block A"
    return f"TURN_OFF:{device.upper().replace(' ', '_')}"


def recommendation_node(state: dict) -> dict:
    from app.agents.pipeline import _build_fallback_recommendations, _llm_call

    profile = state["building_profile"]
    building_type = profile.get("building_type", "commercial_firm")
    constraint_block = state.get("constraint_block", "")
    domain_research = json.dumps(state.get("domain_research", {}), indent=2)

    system_prompt = RECOMMENDATION_SYSTEM.format(
        building_type=building_type,
        constraint_block=constraint_block,
        domain_research=domain_research
    )

    # ── Append historical context to avoid duplicate recommendations ─────────
    hist = state.get("historical_context", {})
    if hist and hist.get("past_recommendations"):
        system_prompt += f"""

HISTORICAL CONTEXT (already recommended — avoid unless recurring):
Past issues: {json.dumps(hist.get('past_recommendations', []), indent=2)}
Past anomaly count: {hist.get('past_anomaly_count', 0)}
Total data points analyzed: {hist.get('total_data_points', 0)}

If the same device appears again with a higher anomaly frequency, escalate severity.
Otherwise, focus on NEW issues not previously addressed.
"""

    # ── Apply prompt override if set via UI ──────────────────────────────────
    overrides = state.get("prompt_overrides", {})
    if overrides.get("Recommendation Agent"):
        system_prompt = overrides["Recommendation Agent"]
        logger.info("Recommendation Agent: Using prompt override from UI.")

    # ── Build human prompt from pipeline state ───────────────────────────────
    actionable_behaviors = [
        b for b in state.get("behaviors", [])
        if b.get("is_actionable", True)
    ]

    human_prompt = json.dumps({
        "actionable_behaviors": actionable_behaviors[:5],
        "savings_estimates": state.get("savings_estimates", [])[:5],
        "live_telemetry_events": state.get("telemetry_events", [])[-5:],
        "anomaly_summary": [
            {
                "device": a.get("device"),
                "kwh": a.get("kwh"),
                "baseline_kwh": a.get("baseline_kwh"),
                "z_score": a.get("z_score"),
                "severity": a.get("severity"),
            }
            for a in state.get("anomalies", [])[:5]
        ]
    }, default=str)

    fallback = _build_fallback_recommendations(state)

    # ── LLM call ─────────────────────────────────────────────────────────────
    recommendations = _llm_call(system_prompt, human_prompt, fallback)

    # ── Validate response ────────────────────────────────────────────────────
    if not isinstance(recommendations, list) or len(recommendations) == 0:
        logger.warning("Recommendation Agent: LLM returned invalid response, using fallback.")
        recommendations = fallback

    # ── Post-process: normalize control actions ──────────────────────────────
    for rec in recommendations:
        device = rec.get("device") or (
            rec.get("issue", "").split("on ")[-1] if "on " in rec.get("issue", "") else "DEVICE"
        )
        rec["control_action"] = _normalize_control_action(
            rec.get("control_action", ""), device
        )
        rec["device"] = device
        # Ensure confidence is a float
        try:
            rec["confidence"] = float(rec.get("confidence", 0.85))
        except (ValueError, TypeError):
            rec["confidence"] = 0.85

    return {
        "recommendations": recommendations,
        "agent_logs": [{
            "agent": "Recommendation Agent",
            "action": "Automation Control Planning",
            "output": (
                f"Generated {len(recommendations)} automation-ready control actions. "
                f"Commands: {[r.get('control_action') for r in recommendations]}"
            ),
            "details": recommendations
        }]
    }
