"""
SustainAI — Context Agent v3
────────────────────────────
Responsibility:
  - Load building profile from state
  - Parse critical_devices JSON safely
  - Build the constraint_block injected into ALL downstream agent prompts
  - Log initialization

No LLM call. Pure deterministic setup. Must never fail.
"""

import json
import logging

logger = logging.getLogger("uvicorn.error")


def context_node(state: dict) -> dict:
    """
    Entry point of the LangGraph pipeline.
    Populates state["constraint_block"] which every downstream agent depends on.
    """
    from app.knowledge.benchmarks import get_constraint_prompt_block

    profile = state.get("building_profile", {})

    # ── Safe parse of critical_devices ──────────────────────────────────────
    critical_raw = profile.get("critical_devices", "[]")
    try:
        critical_devices = json.loads(critical_raw) if isinstance(critical_raw, str) else critical_raw
        if not isinstance(critical_devices, list):
            critical_devices = []
    except (json.JSONDecodeError, TypeError):
        critical_devices = []
        logger.warning("Context Agent: Could not parse critical_devices JSON — defaulting to []")

    # Store parsed list back so downstream agents don't re-parse
    profile["_critical_devices_parsed"] = critical_devices

    # ── Load Device Registry ────────────────────────────────────────────────
    registry = {}
    import os
    registry_paths = ["backend/app/data/device_registry.json", "app/data/device_registry.json"]
    for p in registry_paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    registry = json.load(f)
                break
            except Exception as e:
                logger.warning(f"Context Agent: Failed to load registry: {e}")

    # ── Build constraint block ───────────────────────────────────────────────
    try:
        constraint_block = get_constraint_prompt_block(profile)
        if registry:
            constraint_block += "\n=== DEVICE REGISTRY (ID METADATA) ===\n"
            constraint_block += json.dumps(registry, indent=2)
            constraint_block += "\n=== END REGISTRY ===\n"
    except Exception as e:
        logger.error(f"Context Agent: get_constraint_prompt_block failed: {e}")
        constraint_block = f"""
=== BUILDING CONTEXT ===
Building: {profile.get('building_name', 'Unknown')}
Type: {profile.get('building_type', 'Unknown')}
Critical Devices (NEVER TOUCH): {json.dumps(critical_devices)}
DEVICE REGISTRY: {json.dumps(registry)}
=== END CONTEXT ===
"""

    return {
        "constraint_block": constraint_block,
        "device_registry": registry,
        "agent_logs": [{
            "agent": "Context Agent",
            "action": "Profile Initialization",
            "output": (
                f"Loaded profile for '{profile.get('building_name', 'Unnamed Building')}' "
                f"({profile.get('building_type', 'unknown')} in {profile.get('city', 'India')}). "
                f"Critical devices protected: {critical_devices}"
            ),
            "details": {
                "building_type": profile.get("building_type"),
                "building_name": profile.get("building_name"),
                "city": profile.get("city"),
                "critical_devices": critical_devices,
                "occupancy_hours": profile.get("occupancy_hours"),
            }
        }]
    }
