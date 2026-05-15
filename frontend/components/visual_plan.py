import streamlit as st
import textwrap

def agent_studio_panel(logs, state_data):
    """Advanced studio panel to inspect state and edit behavior."""
    st.markdown(textwrap.dedent("""
        <div style="background: rgba(155, 89, 182, 0.05); padding: 15px; border-radius: 12px; border: 1px solid rgba(155, 89, 182, 0.2); margin-bottom: 20px;">
            <h4 style="margin: 0; color: #9b59b6; font-family: 'Outfit';">🧪 Agent Studio & Prompt Lab</h4>
            <p style="font-size: 0.85rem; color: #888;">Inspect the reasoning engine's internal state and override agent behavior.</p>
        </div>
    """), unsafe_allow_html=True)
    
    col_trace, col_state = st.columns([1, 1])
    
    with col_trace:
        st.markdown("##### 🧶 Trajectory Trace")
        if not logs:
            st.info("No active trajectory. Run analysis to start.")
        else:
            for i, log in enumerate(logs):
                with st.expander(f"{i+1}. {log['agent']} → {log['action']}", expanded=(i == len(logs)-1)):
                    st.markdown(textwrap.dedent(f"""
                        <div style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 5px;">
                            <div style="color: #2d9c6e; font-size: 0.8rem; font-weight: 700; margin-bottom: 5px;">REASONING OUTPUT</div>
                            <div style="color: #eee; font-family: 'Inter'; font-size: 0.95rem; line-height: 1.5;">{log['output']}</div>
                        </div>
                    """), unsafe_allow_html=True)
                    if st.button("✏️ Edit Behavior for this Node", key=f"edit_{i}"):
                        st.info(f"Behavior override for {log['agent']} is now active in the Prompt Lab.")
    
    with col_state:
        st.markdown("##### 🧊 State Inspector")
        if state_data:
            st.json(state_data)
        else:
            st.caption("Current state is empty.")

    st.divider()
    with st.expander("📝 Prompt Lab: Agent Instructions Override"):
        st.markdown("Modify the core logic of your agents. Changes take effect on next reasoning run.")
        agent_to_edit = st.selectbox("Select Agent to Configure", ["Recommendation Agent", "Explanation Agent", "Anomaly Agent"])
        
        default_instruction = "You are a sustainability advisor..."
        if agent_to_edit == "Explanation Agent":
            default_instruction = "Synthesize the findings into a cohesive report..."
            
        custom_instr = st.text_area("System Instruction Override", value=default_instruction, height=150)
        if st.button("💾 Apply Behavior Override"):
            st.session_state[f"override_{agent_to_edit}"] = custom_instr
            st.success(f"Logic for {agent_to_edit} updated. Re-run analysis to see the effect.")

def reasoning_flow_visual(active_node=None):
    """Visual representation of the LangGraph multi-agent reasoning flow with active node highlighting."""
    
    nodes = [
        ("context_node", "Context Agent", "Building Profile Analysis", "#3498db"),
        ("research_node", "Research Agent", "Domain & Standards", "#9b59b6"),
        ("anomaly_node", "Anomaly Agent", "Outlier Detection", "#e74c3c"),
        ("behavior_node", "Behavior Agent", "Pattern Recognition", "#f39c12"),
        ("recommendation_node", "Recommendation Agent", "Constraint-First Logic", "#2ecc71"),
        ("doctor_node", "Doctor Agent", "Verification Auditor", "#34495e"),
        ("explanation_node", "Explanation Agent", "Insight Synthesis", "#8e44ad"),
    ]

    # Generate HTML for nodes
    nodes_html = ""
    for i, (id, name, desc, color) in enumerate(nodes):
        is_active = (active_node == id)
        active_style = f"box-shadow: 0 0 25px {color}; border: 2px solid {color}; transform: scale(1.05); animation: pulse 1.5s infinite;" if is_active else f"border: 1px solid {color}44; background: {color}05; opacity: 0.6;"
        badge_html = f'<div class="node-badge" style="background: {color};">ACTIVE</div>' if is_active else ''
        
        nodes_html += f"""
<div class="node-v" style="{active_style} color: {color};">
{badge_html}
<b>{name}</b>
<span>{desc}</span>
</div>
"""
        if i < len(nodes) - 1:
            nodes_html += '<div class="edge-v"></div>'

    st.markdown(f"""
<div style="margin-top: 20px; padding: 24px; background: rgba(15, 15, 25, 0.4); border-radius: 16px; border: 1px solid rgba(255,255,255,0.08); backdrop-filter: blur(10px);">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
<h4 style="margin: 0; color: #fff; font-family: 'Outfit', sans-serif;">🏗️ Multi-Agent Trajectory</h4>
<div style="display: flex; align-items: center; gap: 8px;">
<div style="width: 8px; height: 8px; background: #2ecc71; border-radius: 50%; animation: pulse 1s infinite;"></div>
<span class="badge" style="background: rgba(45,156,110,0.1); color: #2ecc71; border: 1px solid rgba(45,156,110,0.2);">LIVE EXECUTION</span>
</div>
</div>
<div style="display: flex; flex-direction: column; align-items: center; gap: 0;">
{nodes_html}
</div>
</div>
<style>
    @keyframes pulse {{
        0% {{ opacity: 1; transform: scale(1.05); }}
        50% {{ opacity: 0.7; transform: scale(1.02); }}
        100% {{ opacity: 1; transform: scale(1.05); }}
    }}
    .node-v {{
        padding: 12px 20px;
        border-radius: 12px;
        width: 260px;
        text-align: center;
        display: flex;
        flex-direction: column;
        position: relative;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        background: rgba(255,255,255,0.02);
    }}
    .node-badge {{
        position: absolute;
        top: -10px;
        right: -10px;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 8px;
        font-weight: 900;
        color: white;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }}
    .node-v b {{ font-size: 14px; margin-bottom: 2px; font-family: 'Outfit'; letter-spacing: 0.5px; }}
    .node-v span {{ font-size: 11px; opacity: 0.7; font-family: 'Inter'; }}
    .edge-v {{
        width: 2px;
        height: 20px;
        background: linear-gradient(to bottom, rgba(255,255,255,0.1), rgba(255,255,255,0.02));
    }}
    .badge {{
        padding: 4px 12px;
        border-radius: 100px;
        font-size: 10px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
</style>
""", unsafe_allow_html=True)


def visual_sustainability_plan(recommendations):
    """Visual timeline/roadmap for the sustainability plan."""
    if not recommendations:
        return
        
    st.markdown("### 🗺️ Your Sustainability Roadmap")
    
    with st.container():
        for i, rec in enumerate(recommendations):
            color = "#2d9c6e" if i == 0 else "#3498db" if i == 1 else "#f39c12"
            
            # Use absolute beginning of lines to prevent Streamlit from seeing code blocks
            item_html = f"""<div style="display: flex; gap: 20px; margin-bottom: 20px; align-items: stretch;">
<div style="display: flex; flex-direction: column; align-items: center; width: 40px;">
<div style="width: 36px; height: 36px; border-radius: 50%; background: {color}; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-family: 'Outfit'; z-index: 1; box-shadow: 0 0 15px {color}44;">{i+1}</div>
{f'<div style="width: 2px; flex-grow: 1; background: linear-gradient(to bottom, {color}88, rgba(255,255,255,0.05)); margin-top: 5px;"></div>' if i < len(recommendations)-1 else ''}
</div>
<div class="glass-card" style="flex: 1; padding: 20px; margin-bottom: 0; background: rgba(255,255,255,0.03); border-left: 3px solid {color};">
<h5 style="margin: 0; color: {color}; font-size: 1.1rem; font-family: 'Outfit';">{rec['issue']}</h5>
<p style="margin: 10px 0 15px 0; font-size: 14px; color: #ccc; line-height: 1.6;">{rec['recommendation']}</p>
<div style="display: flex; gap: 12px; flex-wrap: wrap;">
<div style="background: {color}15; color: {color}; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">💰 Savings: {rec['estimated_monthly_loss']}</div>
</div>
</div>
</div>"""
            st.markdown(item_html, unsafe_allow_html=True)

def agent_trace_viewer(logs):
    """LangGraph Studio style trace viewer."""
    if not logs:
        st.info("Run analysis to see agent traces.")
        return
        
    st.markdown("### 🧵 Agent Execution Traces")
    st.markdown('<p style="color:#666; font-size:0.9rem; margin-bottom:20px;">Inspect the step-by-step reasoning and tool calls of each agent.</p>', unsafe_allow_html=True)
    
    for log in logs:
        with st.expander(f"🤖 {log['agent']} - {log['action']}", expanded=False):
            # Styling for the trace content
            st.markdown(f"""
<div style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
<div style="color: #2d9c6e; font-size: 0.8rem; font-weight: 700; margin-bottom: 5px;">OUTPUT CONTENT</div>
<div style="color: #eee; font-family: 'Inter'; font-size: 0.95rem; line-height: 1.5;">{log['output']}</div>
</div>
""", unsafe_allow_html=True)
            
            if log.get("details"):
                st.markdown('<div style="color: #3498db; font-size: 0.8rem; font-weight: 700; margin: 15px 0 5px 0;">STATE DATA / METRICS</div>', unsafe_allow_html=True)
                st.json(log["details"])

