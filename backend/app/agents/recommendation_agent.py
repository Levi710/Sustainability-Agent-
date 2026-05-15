import json

RECOMMENDATION_SYSTEM = """
You are a sustainability advisor specializing in {building_type} buildings.
{constraint_block}

Domain Research:
{domain_research}

Generate exactly 3 actionable recommendations. DO NOT include recommendations for critical devices.
Each recommendation must:
1. Reference a specific time window (e.g. "between 11PM and 6AM on weekdays")
2. Quantify the financial impact in INR/month
3. Be realistic given the building's occupancy pattern
4. Reference a relevant standard or benchmark if applicable
15. If a 'Virtual Sensor' event is detected (VOICE/MOTION), prioritize an immediate automation command to respond to it.
16. If total consumption is high across all appliances, implement 'Load Shedding' by reducing non-critical Inductive loads.

Respond ONLY with a JSON array. Each item:
{{
  "issue": "string",
  "reason": "string",
  "reasoning_proof": "Deep data-backed proof (e.g. 'Detected 4.2kW spike at 2AM vs 0.5kW baseline')",
  "recommendation": "string",
  "control_action": "IoT Command (e.g. SET_HVAC_MODE:ECO or TURN_OFF:LAB_PCS)",
  "estimated_monthly_loss": "string",
  "implementation_effort": "low|medium|high",
  "confidence": 0.9
}}
"""

def recommendation_node(state):
    constraint_block = state["constraint_block"]
    building_type = state["building_profile"].get("building_type", "Unknown")
    domain_research = json.dumps(state.get("domain_research", {}), indent=2)
    system_prompt = RECOMMENDATION_SYSTEM.format(
        building_type=building_type,
        constraint_block=constraint_block,
        domain_research=domain_research
    )
    
    # Historical Context
    hist = state.get("historical_context", {})
    if hist:
        system_prompt += f"\n\nHISTORICAL CONTEXT:\n{json.dumps(hist, indent=2)}\n"
        system_prompt += "Cross-reference current issues with past recommendations to avoid redundancy or to emphasize recurring problems."
    
    # Apply override
    overrides = state.get("prompt_overrides", {})
    if overrides.get("Recommendation Agent"):
        system_prompt = overrides["Recommendation Agent"]
    
    actionable_behaviors = [b for b in state.get("behaviors", []) if b.get("is_actionable", True)]
    
    human_prompt = json.dumps({
        "behaviors": actionable_behaviors[:5],
        "savings_estimates": state.get("savings_estimates", [])[:5],
        "live_telemetry_events": state.get("telemetry_events", [])[-5:], # Pass recent I/O events
    }, default=str)
    
    from app.agents.pipeline import _build_fallback_recommendations, _llm_call
    fallback = _build_fallback_recommendations(state)
    
    recommendations = _llm_call(system_prompt, human_prompt, fallback)
    if not isinstance(recommendations, list) or len(recommendations) == 0:
        recommendations = fallback
        
    state["recommendations"] = recommendations
    state.get("agent_logs", []).append({
        "agent": "Recommendation Agent",
        "action": "Automation Control Planning",
        "output": f"Generated {len(recommendations)} automation-ready control actions.",
        "details": recommendations
    })
    return state
