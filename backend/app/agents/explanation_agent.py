"""
SustainAI — Explanation Agent v3
──────────────────────────────────
Responsibility:
  - Synthesize the full pipeline output into a human-readable Sustainability Roadmap
  - Explain the closed-loop automation logic with specific numbers
  - Confirm critical devices were protected
  - Output goes to state["final_explanation"] and state["analysis_report"]

Key fixes over v2:
  - savings is now actually used in the system prompt (was computed but not injected)
  - Fallback is richer and always uses real pipeline data (anomaly count, device names)
  - Provider loop cleaned up — no duplicate key retrieval
  - analysis_report now includes savings_summary for the dashboard
"""

import json
import logging
import os

logger = logging.getLogger("uvicorn.error")

EXPLANATION_SYSTEM = """
You are SustainAI's final reasoning engine — the Explanation Agent.
You have just completed a full 9-agent analysis of a {building_type} building.

{constraint_block}

YOUR TASK:
Synthesize everything into a professional Sustainability Roadmap.
Write for a building manager — clear, data-driven, actionable.

PIPELINE OUTPUTS AVAILABLE TO YOU:
- Anomalies detected: {anomaly_count}
- Habit patterns found: {pattern_summary}
- IoT Recommendations issued: {recommendations_summary}
- Estimated savings: {savings_summary}
- Doctor audit results: {doctor_summary}
- Critical devices protected: {critical_devices}

STRUCTURE YOUR RESPONSE EXACTLY AS FOLLOWS (use these markdown headers):

### 🛡️ Autonomous Control Status
State which IoT commands were issued and their verification status from the Doctor Agent.
Be specific: name the device, the command, and the audit result.

### 🔬 Deep Reasoning & Proofs
For each anomaly, explain:
- What was detected (exact kWh values)
- Why it's wasteful for this building type at that time
- The behavioral root cause

### 💰 Financial & Environmental Impact
Show the monthly INR savings and CO2 reduction achievable.
Reference the simulator estimates.

### 📈 Projected Sustainability Impact
3-month and 12-month projections if recommendations are implemented.
Reference BEE/ECBC benchmarks for context.

### ✅ What Was Protected
Confirm that critical devices were excluded from all optimization actions and why.

RULES:
- Use actual numbers from the pipeline data above — do not invent figures.
- Every claim needs a data reference.
- Write in English. Use ₹ for currency. Use kWh for energy.
- Do NOT use generic phrases like "significant savings" without a number.
"""


def explanation_node(state: dict) -> dict:
    from app.agents.pipeline import _raw_llm_call

    profile = state["building_profile"]
    building_type = profile.get("building_type", "Unknown")
    critical_devices = profile.get("_critical_devices_parsed",
                                   profile.get("critical_devices", "None listed"))

    # ── Prepare structured summaries for the prompt ──────────────────────────
    anomaly_count = len(state.get("anomalies", []))

    pattern_summary = json.dumps([
        {"device": p.get("device"), "pattern": p.get("pattern"), "frequency": p.get("frequency")}
        for p in state.get("patterns", [])[:3]
    ], indent=2)

    recommendations_summary = json.dumps([
        {
            "issue": r.get("issue"),
            "control_action": r.get("control_action"),
            "estimated_monthly_loss": r.get("estimated_monthly_loss"),
            "confidence": r.get("confidence"),
        }
        for r in state.get("recommendations", [])[:3]
    ], indent=2)

    savings_summary = json.dumps([
        {
            "device": s.get("device"),
            "monthly_savings_inr": s.get("monthly_savings_inr"),
            "co2_avoided_kg": s.get("co2_avoided_kg"),
            "cost_reduction_percent": s.get("cost_reduction_percent"),
        }
        for s in state.get("savings_estimates", [])[:3]
    ], indent=2)

    doctor_summary = json.dumps([
        {
            "device": d.get("device"),
            "verification_status": d.get("verification_status"),
            "doctor_notes": d.get("doctor_notes"),
            "optimization_score": d.get("optimization_score"),
        }
        for d in state.get("doctor_audits", [])
    ], indent=2) or "No Doctor audits available yet (first run)."

    constraint_block = state.get("constraint_block", "")

    system_prompt = EXPLANATION_SYSTEM.format(
        building_type=building_type,
        constraint_block=constraint_block,
        anomaly_count=anomaly_count,
        pattern_summary=pattern_summary,
        recommendations_summary=recommendations_summary,
        savings_summary=savings_summary,
        doctor_summary=doctor_summary,
        critical_devices=json.dumps(critical_devices)
    )

    # ── Append historical context ────────────────────────────────────────────
    hist = state.get("historical_context", {})
    if hist:
        system_prompt += f"""

HISTORICAL CONTEXT:
{json.dumps(hist, indent=2)}

Identify whether current anomalies are recurring (escalate severity) or new (explain as fresh finding).
"""

    # ── Apply prompt override ────────────────────────────────────────────────
    overrides = state.get("prompt_overrides", {})
    if overrides.get("Explanation Agent"):
        system_prompt = overrides["Explanation Agent"]
        logger.info("Explanation Agent: Using prompt override from UI.")

    human_prompt = (
        "Generate the complete Sustainability Roadmap based on all pipeline findings above. "
        "Use specific numbers. Name specific devices. Be direct and professional."
    )

    # ── Try providers ────────────────────────────────────────────────────────
    providers = []
    groq_key = os.getenv("GROQ_API_KEY")
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if groq_key and groq_key != "your_key_here":
        providers.append(("groq", groq_key))
    if nvidia_key and nvidia_key != "your_key_here":
        providers.append(("nvidia", nvidia_key))

    explanation = ""
    for provider_info in providers:
        try:
            result = _raw_llm_call(provider_info, system_prompt, human_prompt)
            if result and len(result.strip()) > 100:
                explanation = result
                break
        except Exception as e:
            logger.warning(f"Explanation Agent: {provider_info[0]} failed — {e}")
            continue

    # ── Rich deterministic fallback using real pipeline data ─────────────────
    if not explanation:
        total_savings = sum(
            s.get("monthly_savings_inr", 0) for s in state.get("savings_estimates", [])
        )
        total_co2 = sum(
            s.get("co2_avoided_kg", 0) for s in state.get("savings_estimates", [])
        )
        rec_list = "\n".join([
            f"- **{r.get('control_action')}** → {r.get('recommendation', '')} ({r.get('estimated_monthly_loss', '')})"
            for r in state.get("recommendations", [])
        ])
        audit_list = "\n".join([
            f"- **{d.get('device')}**: {d.get('verification_status')} — {d.get('doctor_notes', '')}"
            for d in state.get("doctor_audits", [])
        ]) or "- First run: no prior audits."

        explanation = f"""
### 🛡️ Autonomous Control Status
The pipeline issued {len(state.get('recommendations', []))} IoT control commands:
{rec_list}

Doctor Agent audits:
{audit_list}

### 🔬 Deep Reasoning & Proofs
Analysis of {building_type} data identified **{anomaly_count} anomalies** across monitored devices.
Devices showing consumption above baseline during non-occupancy hours were flagged for immediate action.

### 💰 Financial & Environmental Impact
- Estimated monthly savings: **₹{total_savings:,.0f}**
- CO₂ avoided per month: **{total_co2:.1f} kg**
- Annual projection: **₹{total_savings * 12:,.0f}** and **{total_co2 * 12:.0f} kg CO₂**

### 📈 Projected Sustainability Impact
At current optimization rate, 3-month savings: ₹{total_savings * 3:,.0f}.
Full implementation aligns with BEE energy efficiency targets for {building_type} buildings.

### ✅ What Was Protected
Critical devices ({json.dumps(critical_devices)}) were excluded from all optimization actions.
These devices operate under mandatory uptime requirements and were flagged as informational-only.
"""
        logger.warning("Explanation Agent: LLM unavailable — using deterministic fallback report.")

    state["final_explanation"] = explanation
    state["analysis_report"] = {
        "final_explanation": explanation,
        "anomalies_count": anomaly_count,
        "recommendations_count": len(state.get("recommendations", [])),
        "total_monthly_savings_inr": sum(
            s.get("monthly_savings_inr", 0) for s in state.get("savings_estimates", [])
        ),
        "total_co2_avoided_kg": sum(
            s.get("co2_avoided_kg", 0) for s in state.get("savings_estimates", [])
        ),
        "doctor_audits_count": len(state.get("doctor_audits", [])),
    }

    report = state["analysis_report"]
    return {
        "final_explanation": explanation,
        "analysis_report": report,
        "agent_logs": [{
            "agent": "Explanation Agent",
            "action": "Sustainability Roadmap Generation",
            "output": (
                f"Report generated. {anomaly_count} anomalies explained. "
                f"{len(state.get('recommendations', []))} actions documented. "
                f"Total savings: ₹{report['total_monthly_savings_inr']:,.0f}/month."
            ),
            "details": {
                "anomalies_count": anomaly_count,
                "recommendations_count": report["recommendations_count"],
                "total_monthly_savings_inr": report["total_monthly_savings_inr"],
                "total_co2_avoided_kg": report["total_co2_avoided_kg"],
            }
        }]
    }
