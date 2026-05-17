"""
SustainAI — Research Agent v3
──────────────────────────────
Responsibility:
  - Fetch sector-specific energy benchmarks (BEE / ASHRAE / ECBC)
  - Ask LLM to contextualize them for this specific building
  - Populate state["domain_research"] used by Behavior + Recommendation agents

Fallback: Returns structured benchmark data from local benchmarks.py
if LLM is unavailable — pipeline never stalls here.
"""

import json
import logging

logger = logging.getLogger("uvicorn.error")

RESEARCH_SYSTEM = """
You are a certified energy auditor specializing in {building_type} buildings in India.
{constraint_block}

Your task: produce a domain research brief that downstream AI agents will use
to distinguish genuine waste from expected consumption patterns.

RULES:
- Be specific to Indian climate and DISCOM tariff structures.
- Reference actual standards: BEE Star Rating, ECBC 2017, ASHRAE 90.1.
- Do NOT invent consumption numbers — use the benchmark ranges provided.
- Respond ONLY with valid JSON. No markdown. No explanation outside the JSON.

JSON structure (all fields required):
{{
  "building_type_context": "2-sentence description of typical energy profile for this building type in India",
  "seasonal_factors": "How current Indian season affects expected consumption for this building type",
  "regulatory_standards": "Specific BEE/ECBC/ASHRAE standards applicable to this building",
  "critical_usage_windows": "Exact time windows where HIGH consumption is EXPECTED and NORMAL — do not flag these as waste",
  "waste_risk_windows": "Exact time windows where consumption is likely waste for this building type",
  "benchmark_kwh_per_sqft": "Expected monthly kWh/sqft for this building type with source",
  "benchmark_comparison_note": "How to interpret whether measured consumption is high, normal, or low",
  "top_3_waste_drivers": ["driver1", "driver2", "driver3"]
}}
"""


def research_node(state: dict) -> dict:
    from app.knowledge.benchmarks import get_benchmark
    from app.agents.pipeline import _llm_call

    profile = state["building_profile"]
    building_type = profile.get("building_type", "commercial_firm")
    benchmark = get_benchmark(building_type)
    constraint_block = state.get("constraint_block", "")

    system_prompt = RESEARCH_SYSTEM.format(
        building_type=building_type,
        constraint_block=constraint_block
    )

    human_prompt = json.dumps({
        "building_name": profile.get("building_name", "Unknown"),
        "building_type": building_type,
        "city": profile.get("city", "India"),
        "state": profile.get("state", ""),
        "occupancy_hours": profile.get("occupancy_hours", "Standard business hours"),
        "special_constraints": profile.get("special_constraints", "None"),
        "local_benchmark": {
            "avg_kwh_per_sqft_per_month": benchmark["avg_kwh_per_sqft_per_month"],
            "peak_occupancy_hours": benchmark["peak_occupancy_hours"],
            "known_waste_patterns": benchmark["known_waste_patterns"],
        }
    }, indent=2)

    # ── Structured fallback — always valid even if LLM fails ─────────────────
    fallback = {
        "building_type_context": benchmark["description"],
        "seasonal_factors": (
            "High cooling load expected during Indian summers (Mar–Jun). "
            "Heating negligible in most Indian cities. Monsoon season reduces AC load by ~15%."
        ),
        "regulatory_standards": benchmark["benchmark_sources"],
        "critical_usage_windows": benchmark["peak_occupancy_hours"],
        "waste_risk_windows": f"Outside of {benchmark['peak_occupancy_hours']} — any high consumption here is likely waste.",
        "benchmark_kwh_per_sqft": f"{benchmark['avg_kwh_per_sqft_per_month']} kWh/sqft/month ({benchmark['benchmark_sources']})",
        "benchmark_comparison_note": (
            f"Consumption above {benchmark['avg_kwh_per_sqft_per_month']} kWh/sqft/month "
            f"is HIGH for a {building_type}. Within 10% is normal. Below is excellent."
        ),
        "top_3_waste_drivers": benchmark["known_waste_patterns"][:3],
    }

    domain_research = _llm_call(system_prompt, human_prompt, fallback)

    # ── Validate response shape ──────────────────────────────────────────────
    if not isinstance(domain_research, dict):
        logger.warning("Research Agent: LLM returned non-dict, using fallback.")
        domain_research = fallback

    required_keys = ["building_type_context", "waste_risk_windows", "critical_usage_windows"]
    for key in required_keys:
        if key not in domain_research:
            domain_research[key] = fallback.get(key, "")

    return {
        "domain_research": domain_research,
        "agent_logs": [{
            "agent": "Research Agent",
            "action": "Domain Benchmark Retrieval",
            "output": (
                f"Loaded {building_type} benchmarks. "
                f"Waste risk window: {domain_research.get('waste_risk_windows', 'N/A')}. "
                f"Expected: {domain_research.get('benchmark_kwh_per_sqft', 'N/A')}"
            ),
            "details": domain_research
        }]
    }
