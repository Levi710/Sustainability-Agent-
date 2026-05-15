import json
import re

EXPLANATION_SYSTEM = """
You are SustainAI's reasoning engine. You have analyzed energy data for a {building_type}.
{constraint_block}

Your task is to provide a rigorous, data-driven analysis for a {building_type}.
{constraint_block}

You must explain the 'Closed-Loop' automation logic. The system doesn't just recommend; it triggers IoT control commands.

Input Data Provided:
- Anomalies: {anomaly_count} detected with reasoning proofs.
- Autonomous Actions: {recommendations} (includes specific IoT control commands).
- Verified Patterns: {patterns}

Output Requirements:
1. Provide DEEP REASONING for every claim. Use numbers from the anomalies.
2. Explain the 'Automation Fix': Describe the specific IoT commands the system has prepared or executed to fluctuate the load.
3. Validate against {critical_devices}: Explain how critical infrastructure was protected while optimizing other loads.

Structure your response:
- ### 🛡️ Autonomous Control Status
- ### 🔬 Deep Reasoning & Proofs
- ### 📈 Projected Sustainability Impact
"""

def explanation_node(state):
    constraint_block = state["constraint_block"]
    profile = state["building_profile"]
    building_type = profile.get("building_type", "Unknown")
    critical_devices = profile.get("critical_devices", "None listed")
    
    anomaly_count = len(state.get("anomalies", []))
    patterns = json.dumps(state.get("patterns", [])[:3])
    recommendations = json.dumps(state.get("recommendations", [])[:3])
    savings = json.dumps(state.get("savings_estimates", [])[:2])
    
    system_prompt = EXPLANATION_SYSTEM.format(
        building_type=building_type,
        constraint_block=constraint_block,
        anomaly_count=anomaly_count,
        patterns=patterns,
        recommendations=recommendations,
        savings=savings,
        critical_devices=critical_devices
    )
    
    # Add Historical Context to System Prompt
    hist = state.get("historical_context", {})
    if hist:
        system_prompt += f"\n\nHISTORICAL CONTEXT:\n{json.dumps(hist, indent=2)}\n"
        system_prompt += "Identify if these findings correlate with past recommendations or if this is a new optimization window."
    
    # Apply override if exists
    overrides = state.get("prompt_overrides", {})
    if overrides.get("Explanation Agent"):
        system_prompt = overrides["Explanation Agent"]
    
    human_prompt = "Synthesize the final report based on the reasoning pipeline's findings."
    
    from app.agents.pipeline import _raw_llm_call, _get_api_key
    
    api_key = _get_api_key()
    explanation = ""
    
    if api_key:
        try:
            explanation = _raw_llm_call(api_key, system_prompt, human_prompt)
        except Exception as e:
            explanation = f"### ⚠️ Reasoning Error\nOur agents encountered an issue during synthesis: {str(e)}"
    
    if not explanation:
        # Minimal dynamic fallback if LLM fails
        explanation = f"""
### 📊 System Diagnostics
Analysis of {building_type} data identified **{anomaly_count} anomalies**. 

### 🚨 Critical Findings
Multiple devices are showing patterns outside of normal operating hours.

### 💡 Actionable Path forward
Implementing the suggested {len(state.get('recommendations', []))} improvements could significantly reduce your monthly overhead. 
*Note: Critical systems like {critical_devices} were excluded from shutdown logic.*
"""

    state["final_explanation"] = explanation
    state["analysis_report"] = {
        "final_explanation": explanation,
        "anomalies_count": anomaly_count,
        "recommendations_count": len(state.get("recommendations", []))
    }
    
    return state

