import json
from app.knowledge.benchmarks import get_benchmark

def research_node(state):
    profile = state["building_profile"]
    benchmark = get_benchmark(profile["building_type"])
    constraint_block = state["constraint_block"]

    system_prompt = f"""
You are an energy auditing expert specializing in {profile['building_type']} buildings in India.
{constraint_block}

Generate a domain research brief that will guide energy analysis for this specific building.
Respond ONLY with valid JSON. No markdown, no explanation outside JSON.

JSON structure:
{{
  "building_type_context": "2-sentence description of typical energy profile for this building type",
  "seasonal_factors": "how current season affects expected consumption (use India climate context)",
  "regulatory_standards": "relevant BEE/ECBC/ASHRAE standards that apply",
  "critical_usage_windows": "time windows where high consumption is EXPECTED and normal",
  "waste_risk_windows": "time windows where high consumption is likely waste",
  "benchmark_comparison_note": "how to interpret whether measured consumption is high/normal/low"
}}
"""

    human_prompt = f"""
Building: {profile.get('building_name', 'Unknown')}
Type: {profile['building_type']}
Location: {profile.get('city', 'India')}
Occupancy: {profile.get('occupancy_hours', 'Standard')}
Special constraints: {profile.get('special_constraints', 'None')}
"""

    from app.agents.pipeline import _llm_call
    
    fallback = {
        "building_type_context": benchmark["description"],
        "seasonal_factors": "High cooling load expected during Indian summers.",
        "regulatory_standards": benchmark["benchmark_sources"],
        "critical_usage_windows": benchmark["peak_occupancy_hours"],
        "waste_risk_windows": "Outside of " + benchmark["peak_occupancy_hours"],
        "benchmark_comparison_note": f"Consumption above {benchmark['avg_kwh_per_sqft_per_month']} is high."
    }
    
    response_json = _llm_call(system_prompt, human_prompt, fallback)
    state["domain_research"] = response_json
    return state
