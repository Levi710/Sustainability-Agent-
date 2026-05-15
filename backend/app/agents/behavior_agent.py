import json

BEHAVIOR_SYSTEM = """
You are a senior energy behavior analyst.
{constraint_block}

Domain Research Brief:
{domain_research}

Given the anomalies and patterns below, identify the root behavioral cause of each inefficiency.
CRITICAL RULES:
- NEVER recommend action on devices marked as critical or informational.
- Ground your analysis in the domain benchmarks provided.
- If an anomaly happens during an expected high-usage window, say so explicitly.
- If consumption is within benchmark range, say so — do not manufacture problems.

Respond ONLY with a JSON array. Each item:
{{
  "behavior": "string",
  "device": "string",
  "root_cause": "string",
  "is_actionable": true,
  "why_not_actionable": "string or null",
  "occupancy_context": "string",
  "financial_impact": "string",
  "confidence": 0.9
}}
"""

def behavior_node(state):
    constraint_block = state["constraint_block"]
    domain_research = json.dumps(state.get("domain_research", {}), indent=2)
    system_prompt = BEHAVIOR_SYSTEM.format(
        constraint_block=constraint_block,
        domain_research=domain_research
    )
    
    human_prompt = json.dumps({
        "patterns": state.get("patterns", [])[:5],
        "anomalies": state.get("anomalies", [])[:10],
    }, default=str)
    
    fallback = []
    for p in state.get("patterns", []):
        fallback.append({
            "behavior": p["pattern"].replace("_", " ").title(),
            "device": p["device"],
            "root_cause": p.get("description", ""),
            "is_actionable": p.get("actionable", True),
            "why_not_actionable": p.get("note", None),
            "occupancy_context": "Derived from pattern",
            "financial_impact": "Estimated ₹200–₹800/month excess cost",
            "confidence": p.get("confidence", 0.75),
        })

    from app.agents.pipeline import _llm_call
    behaviors = _llm_call(system_prompt, human_prompt, fallback)
    if not isinstance(behaviors, list):
        behaviors = fallback
        
    state["behaviors"] = behaviors
    state.get("agent_logs", []).append({
        "agent": "Behavior Agent",
        "action": "Root Cause Analysis",
        "output": f"Analyzed {len(behaviors)} behavioral patterns across the building.",
        "details": behaviors[:2]
    })
    return state
