def context_node(state):
    """
    Loads building profile from DB for this session.
    Generates the constraint block.
    Parses critical_devices from JSON.
    """
    from app.knowledge.benchmarks import get_constraint_prompt_block
    import json

    profile = state["building_profile"]
    state["constraint_block"] = get_constraint_prompt_block(profile)
    
    state.get("agent_logs", []).append({
        "agent": "Context Agent",
        "action": "Profile Initialization",
        "output": f"Loaded profile for {profile.get('building_name', 'Unnamed Building')}.",
        "details": profile
    })
    return state
