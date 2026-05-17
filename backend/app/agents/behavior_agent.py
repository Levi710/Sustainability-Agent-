"""
SustainAI — Behavior Agent v3
──────────────────────────────
Responsibility:
  - Receive anomalies + patterns from upstream nodes
  - Use LLM to identify ROOT BEHAVIORAL CAUSE of each inefficiency
  - Respect constraint_block: never flag critical devices as actionable
  - Populate state["behaviors"] for Savings + Recommendation agents

Key fix over v2:
  - Fallback now correctly reads pattern["actionable"] flag set by habits.py
  - Caps anomaly input at 10 and pattern input at 5 to stay within token limits
  - Validates LLM response is a list before accepting it
"""

import json
import logging

logger = logging.getLogger("uvicorn.error")

BEHAVIOR_SYSTEM = """
You are a senior energy behavior analyst for {building_type} buildings in India.

{constraint_block}

DOMAIN RESEARCH CONTEXT:
{domain_research}

TASK:
Given the anomalies and recurring patterns below, identify the ROOT BEHAVIORAL CAUSE
of each energy inefficiency. You must explain WHY it is happening, not just WHAT happened.

CRITICAL RULES (violations will disqualify your response):
1. NEVER mark a device from the CRITICAL DEVICES list as is_actionable: true.
2. If anomaly timestamps fall within the CRITICAL USAGE WINDOWS from domain research,
   state that explicitly — do not treat expected-hour consumption as waste.
3. If consumption is within benchmark range, say so. Do not manufacture problems.
4. Each behavior must reference specific kWh values from the anomaly data.
5. financial_impact must be a realistic INR/month estimate, not a placeholder.

Respond ONLY with a valid JSON array. No markdown. No explanation outside JSON.
Each item in the array must have ALL of these fields:
{{
  "behavior": "Short name of the wasteful behavior pattern",
  "device": "Exact device name from the input data",
  "root_cause": "1-2 sentences explaining WHY this is happening behaviorally",
  "is_actionable": true or false,
  "why_not_actionable": "Reason if false (e.g. 'Critical cooling system'), else null",
  "occupancy_context": "Is this during occupied or unoccupied hours?",
  "financial_impact": "Estimated ₹X–₹Y/month excess cost based on kWh deviation",
  "confidence": 0.0 to 1.0
}}
"""


def behavior_node(state: dict) -> dict:
    from app.agents.pipeline import _llm_call

    constraint_block = state.get("constraint_block", "")
    domain_research = state.get("domain_research", {})
    building_type = state["building_profile"].get("building_type", "commercial_firm")

    # ── Parse critical devices for fallback validation ───────────────────────
    import json as _json
    critical_raw = state["building_profile"].get("critical_devices", "[]")
    try:
        critical_devices = (
            _json.loads(critical_raw) if isinstance(critical_raw, str) else critical_raw
        )
    except Exception:
        critical_devices = []
    # Also use pre-parsed list if context agent already did this
    critical_devices = state["building_profile"].get("_critical_devices_parsed", critical_devices)

    patterns = state.get("patterns", [])[:5]
    anomalies = state.get("anomalies", [])[:10]

    system_prompt = BEHAVIOR_SYSTEM.format(
        building_type=building_type,
        constraint_block=constraint_block,
        domain_research=json.dumps(domain_research, indent=2)
    )

    human_prompt = json.dumps({
        "patterns": patterns,
        "anomalies": anomalies,
    }, default=str)

    # ── Deterministic fallback built from pattern data ───────────────────────
    fallback = []
    for p in patterns:
        device = p.get("device", "Unknown")
        is_critical = device in critical_devices
        is_actionable = p.get("actionable", True) and not is_critical

        fallback.append({
            "behavior": p.get("pattern", "unknown").replace("_", " ").title(),
            "device": device,
            "root_cause": p.get("description", "Recurring pattern detected in time-series data."),
            "is_actionable": is_actionable,
            "why_not_actionable": (
                "Critical device — monitoring only, no intervention permitted."
                if is_critical else p.get("note", None)
            ),
            "occupancy_context": "Derived from pattern time window analysis.",
            "financial_impact": f"Estimated ₹{round(p.get('avg_kwh_per_occurrence', 1.0) * 8 * 30):,}–₹{round(p.get('avg_kwh_per_occurrence', 1.0) * 10 * 30):,}/month excess cost",
            "confidence": p.get("confidence", 0.75),
        })

    # ── LLM call with fallback ───────────────────────────────────────────────
    behaviors = _llm_call(system_prompt, human_prompt, fallback)

    # ── Validate response ────────────────────────────────────────────────────
    if not isinstance(behaviors, list) or len(behaviors) == 0:
        logger.warning("Behavior Agent: LLM returned invalid response, using fallback.")
        behaviors = fallback

    # ── Safety pass: enforce critical device protection regardless of LLM ────
    for b in behaviors:
        if b.get("device") in critical_devices:
            b["is_actionable"] = False
            b["why_not_actionable"] = "Critical device — overridden by constraint block."

    actionable_count = sum(1 for b in behaviors if b.get("is_actionable"))
    return {
        "behaviors": behaviors,
        "agent_logs": [{
            "agent": "Behavior Agent",
            "action": "Root Cause Analysis",
            "output": (
                f"Identified {len(behaviors)} behavioral patterns. "
                f"{actionable_count} actionable, {len(behaviors) - actionable_count} protected/informational."
            ),
            "details": behaviors[:3]
        }]
    }
