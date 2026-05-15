import streamlit as st
import pandas as pd
import requests
import textwrap
import json
from components.styles import inject_styles
from components.visual_plan import reasoning_flow_visual, visual_sustainability_plan, agent_trace_viewer, agent_studio_panel

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
inject_styles()
API_URL = "http://127.0.0.1:8000/api"
live_mode = False

# Sidebar Branding
st.sidebar.markdown("""
    <div style="text-align: center; padding: 20px;">
        <h2 style="color: #2d9c6e; margin-bottom: 0;">SustainAI</h2>
        <p style="color: #888; font-size: 0.8rem;">Multi-Agent Intelligence</p>
    </div>
""", unsafe_allow_html=True)

if "session_id" not in st.session_state:
    st.session_state["session_id"] = None
if "analysis_complete" not in st.session_state:
    st.session_state["analysis_complete"] = False

st.markdown('<h1 style="margin-bottom:0;">Step 1: Building Profile & Context</h1>', unsafe_allow_html=True)
st.markdown("""
    <div style="display: flex; gap: 10px; margin-bottom: 20px;">
        <span class="badge" style="background: rgba(45,156,110,0.1); color: #2d9c6e; border: 1px solid rgba(45,156,110,0.2);">● Backend Connected</span>
        <span class="badge" style="background: rgba(52,152,219,0.1); color: #3498db; border: 1px solid rgba(52,152,219,0.2);">⚙️ Automation Engine Active</span>
        <span class="badge" style="background: rgba(155,89,182,0.1); color: #9b59b6; border: 1px solid rgba(155,89,182,0.2);">🤖 Multi-Agent Logic Ready</span>
    </div>
    <p style="color:#888;">Define your building characteristics to guide AI reasoning.</p>
""", unsafe_allow_html=True)

with st.form("building_profile_form"):
    col1, col2 = st.columns(2)
    with col1:
        building_type = st.selectbox("Building Type", ["college", "house", "gov_office", "commercial_firm", "hospital", "data_center"])
        building_name = st.text_input("Building Name", value="Demo Building")
        city = st.text_input("City", value="Delhi")
        state = st.text_input("State", value="Delhi")
    with col2:
        floors = st.number_input("Number of Floors", min_value=1, value=5)
        occupancy_hours = st.text_input("Occupancy Hours (e.g. 9AM-6PM)", value="9AM-6PM")
        critical_devices = st.text_area("Critical Devices (one per line)", value="Server_Room_AC")
        special_constraints = st.text_area("Special Constraints")
        
    submit = st.form_submit_button("Save Profile & Initialize Session")

if submit:
    res = requests.post(f"{API_URL}/building-profile", data={
        "building_type": building_type,
        "building_name": building_name,
        "city": city,
        "state": state,
        "floors": floors,
        "occupancy_hours": occupancy_hours,
        "critical_devices": critical_devices,
        "special_constraints": special_constraints
    })
    if res.status_code == 200:
        data = res.json()
        st.session_state["session_id"] = data["session_id"]
        st.session_state["building_profile"] = {
            "building_type": building_type,
            "building_name": building_name,
            "critical_devices": critical_devices
        }
        st.success(f"Profile saved! Session ID: {data['session_id']}")
    else:
        st.error("Failed to save profile")

st.divider()
st.markdown('<h1 style="margin-bottom:0;">Step 2: Historical Data Analysis</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#888; margin-bottom:20px;">Upload consumption data to trigger the multi-agent pipeline.</p>', unsafe_allow_html=True)

if st.session_state.get("session_id"):
    uploaded_file = st.file_uploader("Upload 30-Day Historical CSV", type=["csv"])
    if uploaded_file:
        if st.button("Upload & Analyze"):
            with st.spinner("Uploading historical data..."):
                res = requests.post(
                    f"{API_URL}/upload/csv",
                    data={"session_id": st.session_state["session_id"]},
                    files={"file": uploaded_file}
                )
            if res.status_code == 200:
                st.success("Data uploaded. Running reasoning pipeline...")
                with st.spinner("AI is analyzing context, anomalies, and behaviors..."):
                    overrides = {
                        "Recommendation Agent": st.session_state.get("override_Recommendation Agent"),
                        "Explanation Agent": st.session_state.get("override_Explanation Agent"),
                        "Anomaly Agent": st.session_state.get("override_Anomaly Agent")
                    }
                    overrides = {k: v for k, v in overrides.items() if v}
                    
                    ana_res = requests.post(
                        f"{API_URL}/analyze",
                        json={
                            "session_id": st.session_state["session_id"],
                            "prompt_overrides": overrides
                        }
                    )
                if ana_res.status_code == 200:
                    data = ana_res.json()
                    st.session_state["analysis_complete"] = True
                    st.session_state["agent_logs"] = data.get("agent_logs", [])
                    st.session_state["analysis_report"] = data.get("report", {})
                    
                    # Update local data for charts (Fetch FULL history for sync)
                    usage_res = requests.get(f"{API_URL}/data/{st.session_state['session_id']}")
                    if usage_res.status_code == 200:
                        st.session_state["df"] = usage_res.json().get("data", [])
                    else:
                        # Fallback to latest upload if fetch fails
                        uploaded_file.seek(0)
                        st.session_state["df"] = pd.read_csv(uploaded_file).to_dict('records')
                    
                    st.success("Analysis complete!")
                    st.rerun()
                else:
                    st.error(f"Analysis failed: {ana_res.text}")

    if st.session_state.get("analysis_complete"):
        st.divider()
        report = st.session_state.get("analysis_report", {})
        
        st.markdown(f"""
<div class="glass-card" style="margin-top: 24px; border-top: 4px solid #2d9c6e;">
<h3 style="margin-top: 0; color: #2d9c6e; font-family: 'Outfit';">📋 Agent Executive Summary</h3>
<div style="font-size: 1.1rem; line-height: 1.7; color: #eee; font-family: 'Inter';">
{report.get("final_explanation", "No explanation available.")}
</div>
</div>
""", unsafe_allow_html=True)
        
        tab_overview, tab_traces, tab_chat, tab_studio = st.tabs(["📊 Reasoning Overview", "🧵 Trajectory Trace", "💬 Expert Consultation", "🧪 Agent Studio"])
        
        with tab_overview:
            col_main, col_side = st.columns([2, 1])
            
            with col_main:
                st.markdown('<h2 style="margin-top:0;">Sustainability Roadmap</h2>', unsafe_allow_html=True)
                
                # Interactive What-If Section
                st.markdown("""
<div style="background: rgba(45,156,110,0.05); padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px dashed #2d9c6e;">
<h4 style="margin-top:0; color: #2d9c6e;">🛠️ Interactive What-If Simulator</h4>
<p style="font-size: 0.9rem; color: #888;">Toggle recommendations to see projected monthly savings impact.</p>
</div>
""", unsafe_allow_html=True)
                
                # Live Monitoring Toggle
                live_mode = st.sidebar.checkbox("📡 Live Dashboard Sync", value=False)
                active_agent_node = None
                if live_mode:
                    st.sidebar.info("Dashboard is auto-syncing with AI agents every 5s.")
                    try:
                        status_res = requests.get(f"{API_URL}/telemetry/status/{st.session_state['session_id']}")
                        if status_res.status_code == 200:
                            active_agent_node = status_res.json().get("active_node")
                    except:
                        pass

                # Intelligent Grouping Logic
                def get_category(issue):
                    issue = issue.lower()
                    if any(x in issue for x in ["ac", "hvac", "chiller", "cooling"]): return "❄️ HVAC & Cooling"
                    if any(x in issue for x in ["light", "bulb", "led", "lamp"]): return "💡 Lighting Systems"
                    if any(x in issue for x in ["pc", "computer", "server", "ups"]): return "🖥️ IT & Electronics"
                    return "🛠️ General Maintenance"

                try:
                    res_recs = requests.get(f"{API_URL}/recommendations/{st.session_state['session_id']}")
                    if res_recs.status_code == 200:
                        recs = res_recs.json()
                        
                        # Fetch intelligence (logs and audits) for all tabs
                        intel_data = {"agent_logs": [], "doctor_audits": []}
                        try:
                            intel_res = requests.get(f"{API_URL}/intelligence/{st.session_state['session_id']}")
                            if intel_res.status_code == 200:
                                intel_data = intel_res.json()
                        except:
                            pass

                        # Tabs for cleaner navigation
                        tab_priority, tab_assets, tab_audit = st.tabs(["🚀 Priority Actions", "🏢 Asset Classes", "🏥 Audit Trail"])
                        
                        with tab_priority:
                            # ... (baseline/live split)
                            baseline_recs = [r for r in recs if r.get('triggered_by') != 'telemetry_auto']
                            live_recs = [r for r in recs if r.get('triggered_by') == 'telemetry_auto']

                            if live_mode:
                                st.write("### 📡 Live Autonomous Interventions")
                                if live_recs:
                                    for i, r in enumerate(reversed(live_recs[-3:])):
                                        with st.expander(f"⚡ LIVE ACTION: {r['issue']}", expanded=True):
                                            st.success(f"**Verification Status:** {r.get('confidence', 0)*100:.0f}% Confidence")
                                            st.markdown(f"**Reasoning Proof:** {r.get('reasoning_proof')}")
                                            st.code(f"IoT Command: {r.get('control_action')}", language="bash")
                                else:
                                    st.info("Watching sensors... No live intervention required yet.")
                                st.divider()
                            
                            st.write("### 🏢 Baseline Strategic Plan")
                            # De-duplicate issues to show only the latest strategy per asset
                            unique_baseline = []
                            seen_issues = set()
                            for r in baseline_recs:
                                if r['issue'] not in seen_issues:
                                    unique_baseline.append(r)
                                    seen_issues.add(r['issue'])

                            if unique_baseline:
                                for i, r in enumerate(unique_baseline[:3]):
                                    with st.expander(f"📋 STRATEGY: {r['issue']}", expanded=(not live_mode and i==0)):
                                        st.markdown(f"**Recommendation:** {r.get('recommendation')}")
                                        st.info(f"**Impact:** {r.get('estimated_monthly_loss')} potential monthly savings")
                            else:
                                st.info("Run Initial Analysis to generate a baseline strategy.")
                            
                            if not live_mode:
                                st.caption("💡 *System is in 'Default Mode'. Strategic plan is based on historical patterns. Enable 'Live Sync' to see real-time corrections.*")
                        
                        with tab_assets:
                            st.write("### Asset Performance Hub")
                            # Categorize all recommendations
                            categories = {}
                            for r in recs:
                                cat = get_category(r['issue'])
                                if cat not in categories: categories[cat] = []
                                categories[cat].append(r)
                            
                            for cat, items in categories.items():
                                with st.expander(f"{cat} ({len(items)} issues detected)"):
                                    for i, r in enumerate(items):
                                        st.markdown(f"**{r['issue']}**")
                                        st.caption(f"Reason: {r.get('reason', 'N/A')}")
                                        st.markdown("---")

                        with tab_audit:
                            st.write("### Verification Log")
                            audits = intel_data.get("doctor_audits", [])
                            if audits:
                                for a in audits[:15]:
                                    status = a.get('verification_status', 'PENDING')
                                    st.write(f"[{status}] {a.get('device')} - {a.get('doctor_notes')}")
                            else:
                                st.info("No audit logs yet.")

                        visual_sustainability_plan(baseline_recs)
                except Exception as e:
                    st.error(f"Error loading grouped roadmap: {e}")


            with col_side:
                st.markdown('<h2 style="margin-top:0;">Anomaly Summary</h2>', unsafe_allow_html=True)
                anom_res = requests.get(f"{API_URL}/anomalies/{st.session_state['session_id']}")
                if anom_res.status_code == 200:
                    anoms = anom_res.json()
                    if not anoms:
                        st.info("No anomalies detected.")
                    else:
                        st.markdown(f"**{len(anoms)} anomalies found**")
                        
                        search_q = st.text_input("🔍 Search Anomalies", placeholder="e.g. HVAC")
                        filtered_anoms = [a for a in anoms if search_q.lower() in a['device'].lower() or search_q.lower() in a['reason'].lower()]
                        
                        # Show top 4
                        for a in filtered_anoms[:4]:
                            color = "#e74c3c" if a['severity'] == 'high' else "#f39c12"
                            st.markdown(textwrap.dedent(f"""
                                <div style="padding: 10px; border-left: 3px solid {color}; background: rgba(255,255,255,0.02); margin-bottom: 8px; border-radius: 4px;">
                                    <div style="font-size: 13px; font-weight: 700; color: {color};">{a['device']}</div>
                                    <div style="font-size: 12px; margin-top: 4px;">{a['reason']}</div>
                                </div>
                            """), unsafe_allow_html=True)
                            
                        if len(filtered_anoms) > 4:
                            with st.expander(f"View {len(filtered_anoms)-4} More Anomalies"):
                                for a in filtered_anoms[4:]:
                                    color = "#e74c3c" if a['severity'] == 'high' else "#f39c12"
                                    st.markdown(textwrap.dedent(f"""
                                        <div style="padding: 10px; border-left: 3px solid {color}; background: rgba(255,255,255,0.02); margin-bottom: 8px; border-radius: 4px;">
                                            <div style="font-size: 13px; font-weight: 700; color: {color};">{a['device']}</div>
                                            <div style="font-size: 12px; margin-top: 4px;">{a['reason']}</div>
                                        </div>
                                    """), unsafe_allow_html=True)
                
            with st.sidebar:
                st.divider()
                st.subheader("🛡️ System Resilience")
                
                # Determine status from latest recommendation metadata
                is_backup = False
                try:
                    res = requests.get(f"{API_URL}/recommendations/{st.session_state['session_id']}")
                    if res.status_code == 200 and res.json():
                        latest = res.json()[-1]
                        if "Static Memory" in latest.get('reasoning_proof', ''):
                            is_backup = True
                except:
                    pass

                if is_backup:
                    st.warning("🔄 MODE: STATIC MEMORY")
                    st.caption("AI connection lost. Replaying last 50 verified decisions for grid safety.")
                else:
                    st.success("🟢 MODE: LIVE AI ACTIVE")
                    st.caption("Deep reasoning agents are online via Groq/NVIDIA.")
                
                st.divider()

                st.markdown("### 🤖 Live Agent Activity")
                tel_recs_res = requests.get(f"{API_URL}/recommendations/{st.session_state['session_id']}")
                if tel_recs_res.status_code == 200:
                    tel_recs = [r for r in tel_recs_res.json() if r['triggered_by'] == 'telemetry_auto']
                    if tel_recs:
                        for tr in tel_recs[:5]:
                            st.markdown(textwrap.dedent(f"""
                                <div style="background: rgba(45,156,110,0.1); padding: 10px; border-radius: 8px; border-left: 4px solid #2d9c6e; margin-bottom: 10px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <span style="font-weight: bold; color: #2d9c6e;">AUTO-ACTION</span>
                                        <span style="font-size: 10px; opacity: 0.6;">JUST NOW</span>
                                    </div>
                                    <div style="font-size: 14px; margin: 5px 0;">{tr['issue']}</div>
                                    <code style="font-size: 11px;">{tr.get('control_action', 'SET_STATE:OPTIMIZED')}</code>
                                </div>
                            """), unsafe_allow_html=True)
                    else:
                        st.info("Agent is monitoring. Start Telemetry to see real-time corrections.")

                st.divider()
                if st.button("🔄 Reset & Fork Reasoning"):
                    st.session_state["analysis_complete"] = False
                    st.rerun()

        with tab_traces:
            reasoning_flow_visual(active_node=active_agent_node)
            agent_trace_viewer(intel_data.get("agent_logs", []))

        with tab_chat:
            # ... (chat logic)
            st.markdown("### 💬 Expert Consultation")
            
            # Show latest proofs to prove communication
            recs_for_chat_res = requests.get(f"{API_URL}/recommendations/{st.session_state['session_id']}")
            if recs_for_chat_res.status_code == 200:
                recs_for_chat = recs_for_chat_res.json()
                if recs_for_chat:
                    with st.expander("📝 Latest Agent Proofs (Current Context)", expanded=False):
                        for r in recs_for_chat[:2]:
                            st.caption(f"**{r['issue']}**: {r.get('reasoning_proof')}")

            if "chat_messages" not in st.session_state:
                st.session_state.chat_messages = []
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            if prompt := st.chat_input("Ask about your sustainability plan..."):
                st.session_state.chat_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    with st.spinner("Agents conferring..."):
                        chat_res = requests.post(f"{API_URL}/chat", json={"session_id": st.session_state["session_id"], "message": prompt})
                        response = chat_res.json().get("response") if chat_res.status_code == 200 else "Error."
                        st.markdown(response)
                        st.session_state.chat_messages.append({"role": "assistant", "content": response})

        with tab_studio:
            current_logs = intel_data.get("agent_logs", [])
            state_to_inspect = {
                "building_profile": st.session_state.get("building_profile"),
                "agent_logs": current_logs
            }
            agent_studio_panel(current_logs, state_to_inspect)

    # Final live sync trigger
    if live_mode:
        import time
        time.sleep(5)
        st.rerun()
else:
    st.warning("Please initialize a Building Profile to start.")
