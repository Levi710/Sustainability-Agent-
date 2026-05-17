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
                    # Use a non-indented block for the HTML to avoid code blocks
                    output_html = f"""
<div style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 5px;">
<div style="color: #2d9c6e; font-size: 0.8rem; font-weight: 700; margin-bottom: 5px;">REASONING OUTPUT</div>
<div style="color: #eee; font-family: 'Inter'; font-size: 0.95rem; line-height: 1.5;">{log['output']}</div>
</div>
"""
                    st.markdown(output_html, unsafe_allow_html=True)
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
        agent_to_edit = st.selectbox("Select Agent to Configure", ["Recommendation Agent", "Explanation Agent", "Surveillance Agent"])
        
        default_instruction = "You are a sustainability advisor..."
        if agent_to_edit == "Explanation Agent":
            default_instruction = "Synthesize the findings into a cohesive report..."
            
        custom_instr = st.text_area("System Instruction Override", value=default_instruction, height=150)
        if st.button("💾 Apply Behavior Override"):
            st.session_state[f"override_{agent_to_edit}"] = custom_instr
            st.success(f"Logic for {agent_to_edit} updated. Re-run analysis to see the effect.")


def reasoning_flow_visual(active_node=None):
    """Visual representation of the LangGraph multi-agent reasoning flow with true orthogonal edge routing."""
    
    layers = {
        "context": ("context_node", "Context Agent", "Building Profile", "#3498db"),
        "intel": [
            ("research_node", "Research Agent", "Domain Standards", "#9b59b6"),
            ("surveillance_node", "Surveillance Agent", "Fleet Surveillance", "#e74c3c")
        ],
        "analysis": [
            ("behavior_node", "Behavior Agent", "Pattern Logic", "#f39c12"),
            ("recommendation_node", "Recommendation Agent", "Fix Logic", "#2ecc71")
        ],
        "audit": ("doctor_node", "Doctor Agent", "Verification", "#5a6b7c"),
        "synthesis": ("explanation_node", "Explanation Agent", "Final Digest", "#8e44ad")
    }

    def render_node(id, name, desc, color):
        is_active = (active_node == id)
        
        # Enhanced text contrast and conditional execution status glow ring
        active_style = f"box-shadow: 0 0 25px {color}88; border: 2px solid {color}; transform: scale(1.02); z-index: 10;" if is_active else f"border: 1px solid {color}44; background: rgba(15,17,26,0.95); opacity: 0.75;"
        badge = f'<div class="node-badge" style="background: {color};">ACTIVE</div>' if is_active else ''
        
        return f'<div class="node-v" style="{active_style}">{badge}<div class="port top-port"></div><div style="color: #f1f5f9; font-size: 14px; font-weight: 600; font-family: \'Outfit\'; margin-bottom: 2px;">{name}</div><div style="color: #94a3b8; font-size: 11px; font-weight: 500; font-family: \'Inter\';">{desc}</div><div class="port bottom-port"></div></div>'

    # Build the HTML with ZERO INDENTATION to avoid code blocks
    html = f"""
<div style="text-align: center; margin-bottom: 20px;">
<h3 style="margin: 0; color: #fff; font-family: 'Outfit'; letter-spacing: 0.5px;">🏗️ MULTI-AGENT ORCHESTRATION</h3>
<p style="color: #2ecc71; font-size: 10px; font-weight: 800; letter-spacing: 2px; margin-top: 4px;">NON-LINEAR REASONING WEB</p>
</div>

<div class="orchestration-web">
<!-- Context Layer -->
{render_node(*layers['context'])}

<!-- Orthogonal Fork Splitter -->
<div class="elbow-container">
<div class="vertical-line" style="height: 20px;"></div>
<div class="horizontal-bar" style="width: 260px;"></div>
<div class="split-lines-container" style="width: 260px; display: flex; justify-content: space-between;">
<div class="vertical-line" style="height: 20px;"></div>
<div class="vertical-line" style="height: 20px;"></div>
</div>
</div>

<!-- Intel Layer -->
<div class="node-row" style="display: flex; justify-content: center; width: 100%; gap: 40px;">
{render_node(*layers['intel'][0])}
{render_node(*layers['intel'][1])}
</div>

<!-- Parallel Step Connector -->
<div class="split-lines-container" style="width: 260px; margin: 0 auto; display: flex; justify-content: space-between;">
<div class="vertical-line" style="height: 35px;"></div>
<div class="vertical-line" style="height: 35px;"></div>
</div>

<!-- Analysis Layer -->
<div class="node-row" style="display: flex; justify-content: center; width: 100%; gap: 40px;">
{render_node(*layers['analysis'][0])}
{render_node(*layers['analysis'][1])}
</div>

<!-- Orthogonal Merge Joiner -->
<div class="elbow-container">
<div class="split-lines-container" style="width: 260px; display: flex; justify-content: space-between;">
<div class="vertical-line" style="height: 20px;"></div>
<div class="vertical-line" style="height: 20px;"></div>
</div>
<div class="horizontal-bar" style="width: 260px;"></div>
<div class="vertical-line" style="height: 20px;"></div>
</div>

<!-- Audit Layer -->
{render_node(*layers['audit'])}

<div class="vertical-line" style="height: 35px;"></div>

<!-- Synthesis Layer -->
{render_node(*layers['synthesis'])}
</div>

<style>
.orchestration-web {{ display: flex; flex-direction: column; align-items: center; padding: 25px 25px 10px 25px; background: #07080d; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); }}
.node-v {{ padding: 14px 20px; border-radius: 12px; width: 220px; text-align: center; position: relative; background: #0f111a; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }}
.node-badge {{ position: absolute; top: -9px; right: 12px; padding: 1px 7px; border-radius: 4px; font-size: 8px; font-weight: 900; color: white; letter-spacing: 0.5px; box-shadow: 0 2px 8px rgba(0,0,0,0.5); animation: pulse 2s infinite; }}
.port {{ position: absolute; left: 50%; transform: translateX(-50%); width: 7px; height: 7px; background: #475569; border: 1.5px solid #0f111a; border-radius: 50%; }}
.top-port {{ top: -4px; }}
.bottom-port {{ bottom: -4px; }}
.elbow-container {{ display: flex; flex-direction: column; align-items: center; width: 100%; }}
.vertical-line {{ width: 2px; background: #334155; }}
.horizontal-bar {{ height: 2px; background: #334155; }}
@keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.6; }} 100% {{ opacity: 1; }} }}
</style>
"""
    st.markdown(html, unsafe_allow_html=True)


def visual_sustainability_plan(recommendations):
    """Visual timeline/roadmap for the sustainability plan."""
    if not recommendations:
        return
        
    st.markdown("### 🗺️ Your Sustainability Roadmap")
    
    for i, rec in enumerate(recommendations):
        color = "#2d9c6e" if i == 0 else "#3498db" if i == 1 else "#f39c12"
        item_html = f"""
<div style="display: flex; gap: 20px; margin-bottom: 20px; align-items: stretch;">
<div style="display: flex; flex-direction: column; align-items: center; width: 40px;">
<div style="width: 36px; height: 36px; border-radius: 50%; background: {color}; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-family: 'Outfit'; z-index: 1; box-shadow: 0 0 15px {color}44;">{i+1}</div>
{f'<div style="width: 2px; flex-grow: 1; background: linear-gradient(to bottom, {color}88, rgba(255,255,255,0.05)); margin-top: 5px;"></div>' if i < len(recommendations)-1 else ''}
</div>
<div class="glass-card" style="flex: 1; padding: 20px; margin-bottom: 0; background: rgba(255,255,255,0.03); border-left: 3px solid {color}; border-radius: 8px;">
<h5 style="margin: 0; color: {color}; font-size: 1.1rem; font-family: \'Outfit\';">{rec.get('issue', 'Optimization Opportunity')}</h5>
<p style="margin: 10px 0 15px 0; font-size: 14px; color: #ccc; line-height: 1.6;">{rec['recommendation']}</p>
<div style="display: flex; gap: 12px; flex-wrap: wrap;">
<div style="background: {color}15; color: {color}; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">💰 Savings: {rec.get('estimated_monthly_loss', 'N/A')}</div>
</div>
</div>
</div>"""
        st.markdown(item_html, unsafe_allow_html=True)


def agent_trace_viewer(grouped_logs, active_agent=None):
    """Refined trace viewer with execution visualization."""
    pass
