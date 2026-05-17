import streamlit as st
import pandas as pd
import requests
import json
import time
import sys
import os
from datetime import datetime

# Import components and utils
sys.path.append(os.path.dirname(__file__))
from utils import API_BASE_URL, init_state, set_page
from components.visual_plan import reasoning_flow_visual, visual_sustainability_plan, agent_studio_panel

# Configuration
API_URL = API_BASE_URL

def run_dashboard():
    # 1. State Guard
    init_state()
    if "live_mode" not in st.session_state: st.session_state["live_mode"] = True
    if "analysis_complete" not in st.session_state: st.session_state["analysis_complete"] = False
    if "analysis_in_progress" not in st.session_state: st.session_state["analysis_in_progress"] = False

    st.set_page_config(page_title="SustainAI Studio V3", layout="wide", initial_sidebar_state="expanded")

    # 2. Universal Premium CSS
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@300;400;600&display=swap');
    .stApp { background-color: #0f111a; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Outfit', sans-serif; font-weight: 800; letter-spacing: -0.5px; }
    .glass-card { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 20px; margin-bottom: 15px; }
    .heartbeat { animation: pulse 1.5s infinite; color: #2ecc71; font-weight: 800; font-size: 0.75rem; letter-spacing: 1px; }
    @keyframes pulse { 0% { opacity: 0.3; } 50% { opacity: 1; } 100% { opacity: 0.3; } }
    </style>
    """, unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("<h2 style='color: #2d9c6e; margin-bottom:0;'>SustainAI</h2>", unsafe_allow_html=True)
        
        # Check health every 15 seconds to avoid blocking the main UI thread on every tick
        import time
        now_ts = time.time()
        if "api_online" not in st.session_state or now_ts - st.session_state.get("last_health_check", 0) > 15:
            st.session_state["api_online"] = False
            try:
                if requests.get(f"{API_URL}/health", timeout=1).status_code == 200:
                    st.session_state["api_online"] = True
            except:
                pass
            st.session_state["last_health_check"] = now_ts
        api_online = st.session_state["api_online"]
        
        if api_online: st.success("🟢 CORE ENGINE ONLINE")
        else: st.error("🔴 CORE ENGINE OFFLINE")
        
        st.divider()
        st.subheader("🏢 Building Setup")
        b_name = st.text_input("Facility Name", "ABB Innovation Hub")
        b_type = st.selectbox("Infrastructure Type", ["Manufacturing", "Hospital", "College", "Institute", "Office", "Data Center", "Theater", "House"])
        critical_devices = st.text_area(
            "Protected / Critical Devices",
            "DEV_SRV_01\nEmergency_Ward\nICU_HVAC",
            help="One per line. Agents must not reduce or shut down these systems."
        )
        constraints = st.text_area(
            "Operating Constraints",
            "Do not alter emergency, server, ICU, or safety-critical systems without manual approval."
        )
        
        if st.button("Initialize Studio Session", use_container_width=True):
            payload = {"building_type": b_type, "building_name": b_name, "city": "Remote", "state": "Remote", "floors": 1, "occupancy_hours": "24/7", "critical_devices": critical_devices, "special_constraints": constraints}
            try:
                r = requests.post(f"{API_URL}/api/building-profile", data=payload, timeout=5)
                if r.status_code == 200:
                    st.session_state["session_id"] = r.json()["session_id"]
                    st.session_state["building_profile"] = payload
                    st.success("Session Locked!")
                    st.rerun()
                else:
                    st.error(f"API Error ({r.status_code}): {r.text}")
            except Exception as e:
                st.error(f"Connection Failed: {type(e).__name__} - {str(e)}")

    if not st.session_state.get("session_id"):
        st.warning("Please click 'Initialize Studio Session' in the sidebar to enter the dashboard.")
        return

    # Header & Global Controls
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title(f"🚀 {st.session_state['building_profile']['building_name']}")
    with col_h2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.session_state["live_mode"] = st.toggle("📡 Live Dashboard Sync", value=st.session_state["live_mode"])
        if st.session_state["live_mode"]: st.markdown("<div class='heartbeat'>● ANALYTICS STREAM ACTIVE</div>", unsafe_allow_html=True)

    # --- UNIFIED DASHBOARD STATE FETCH ---
    dashboard_data = {"recommendations": [], "anomalies": [], "logs": [], "audits": [], "report": {}, "active_node": "Idle", "control_signals": []}
    if st.session_state.get("session_id"):
        try:
            res = requests.get(f"{API_URL}/api/dashboard-state/{st.session_state['session_id']}")
            if res.status_code == 200: 
                dashboard_data = res.json()
        except: pass

    active_node = dashboard_data.get("active_node", "Idle")

    # If the backend is active, we force "analysis_in_progress" to true
    if active_node not in ["Idle", "Reasoning Failed", "System Offline"]:
        st.session_state["analysis_in_progress"] = True
    else:
        # If it was in progress, we only set it to completed if the thread had time to boot
        if st.session_state.get("analysis_in_progress"):
            elapsed = time.time() - st.session_state.get("analysis_start_time", 0)
            if elapsed > 4.0:
                st.session_state["analysis_in_progress"] = False
                st.session_state["analysis_complete"] = True
                st.rerun()

    # Ingestion Block
    with st.expander("📂 Data Ingestion (Manual Upload)", expanded=not st.session_state.get("analysis_complete", False)):
        up_file = st.file_uploader("Select Telemetry CSV", type=["csv"])
        if up_file:
            if st.button("🚀 Execute Multi-Agent Orchestration", use_container_width=True):
                with st.spinner("Uploading and starting AI agents..."):
                    import io
                    st.session_state.df = pd.read_csv(io.BytesIO(up_file.getvalue()))
                    
                    f = {"file": ("data.csv", up_file.getvalue(), "text/csv")}
                    d = {"session_id": st.session_state["session_id"]}
                    try:
                        r = requests.post(f"{API_URL}/api/upload/csv", files=f, data=d)
                        if r.status_code == 200:
                            # TRIGGER ASYNC ANALYSIS
                            analyze_payload = {"session_id": st.session_state["session_id"]}
                            a_res = requests.post(f"{API_URL}/api/analyze", json=analyze_payload, timeout=5)
                            if a_res.status_code == 200:
                                st.session_state["analysis_in_progress"] = True
                                st.session_state["analysis_start_time"] = time.time()
                                st.success("Analysis started! Watch the Orchestration Graph below.")
                                st.rerun()
                            else:
                                st.error(f"Analysis Trigger Failed ({a_res.status_code}): {a_res.text}")
                        else:
                            st.error(f"Upload Failed ({r.status_code}): {r.text}")
                    except Exception as e:
                        st.error(f"Execution Failed: {str(e)}")

    # Surveillance Block
    with st.expander("Full Infrastructure Surveillance", expanded=False):
        st.caption("Polls every registered IoT device in one snapshot. Non-response becomes a maintenance alert.")
        col_surv_a, col_surv_b = st.columns([1, 1])
        with col_surv_a:
            force_anomaly = st.toggle("Force one anomaly for demo", value=True)
        with col_surv_b:
            if st.button("Run Surveillance Snapshot", use_container_width=True):
                try:
                    r = requests.post(
                        f"{API_URL}/api/telemetry/surveillance-snapshot",
                        json={"session_id": st.session_state["session_id"], "force_anomaly": force_anomaly},
                        timeout=10,
                    )
                    if r.status_code == 200:
                        st.session_state["last_surveillance"] = r.json()
                        st.session_state["analysis_in_progress"] = True # It triggers pipeline in background
                        st.session_state["analysis_start_time"] = time.time()
                        st.success("Surveillance snapshot captured. AI analysis triggered.")
                        st.rerun()
                    else:
                        st.error(f"Surveillance failed ({r.status_code}): {r.text}")
                except Exception as e:
                    st.error(f"Surveillance connection failed: {e}")
        if st.session_state.get("last_surveillance"):
            st.json(st.session_state["last_surveillance"].get("summary", {}))

    # --- THE UNIFIED DATA STREAM (Already fetched at top of page) ---
    pass

    # 1. Orchestration Graph
    if st.session_state["analysis_in_progress"]:
        st.markdown(f"<div style='text-align:center; padding:10px; background:rgba(46, 204, 113, 0.1); border-radius:8px; border:1px solid #2ecc71;'>⚡ <b>AI Agent Active:</b> {active_node.replace('_', ' ').title()} is currently reasoning...</div>", unsafe_allow_html=True)
    
    reasoning_flow_visual(active_node=active_node)
    st.divider()

    # 2. Main Dashboard Layout
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        # Strategy Hub
        st.subheader("🏢 Baseline Strategic Plan")
        baseline = [r for r in dashboard_data["recommendations"] if r.get('triggered_by') != 'telemetry_auto']
        if baseline:
            visual_sustainability_plan(baseline)
        else:
            if not st.session_state["analysis_in_progress"]:
                st.info("No strategy generated. Run orchestration to begin.")
            else:
                st.info("Generating your sustainability roadmap... please wait.")
        
        # Live Reasoning Trace
        st.divider()
        st.subheader("🧶 Real-Time Reasoning Trace")
        if dashboard_data["logs"]:
            grouped = {}
            for log in dashboard_data["logs"]:
                grouped.setdefault(log.get("agent", "Unknown Agent"), []).append(log)
            
            agent_names = list(grouped.keys())
            selected_agent = st.selectbox("Inspect Agent Logs", agent_names, index=len(agent_names)-1)
            for l in grouped.get(selected_agent, []):
                with st.expander(f"{l.get('timestamp', '')} | {l.get('action')}"):
                    st.write(l.get('output'))
                    if l.get("device"): st.caption(f"Device: {l.get('device')}")
                    if l.get("details"): st.json(l.get("details"))
        else:
            st.caption("Awaiting AI coordination logs...")

        report = dashboard_data.get("report", {})
        if report.get("final_explanation"):
            st.divider()
            st.subheader("Final Explanation")
            st.markdown(report["final_explanation"])

    with col_right:
        # Anomaly Alerts
        st.subheader("🚨 Anomaly Center")
        if dashboard_data["anomalies"]:
            for a in dashboard_data["anomalies"][:5]:
                c = "#e74c3c" if a.get('severity') == 'high' else "#f39c12"
                st.markdown(f"<div style='padding:12px; border-left:4px solid {c}; background:rgba(255,255,255,0.03); margin-bottom:10px; border-radius:4px;'><div style='font-size:12px; font-weight:800; color:{c};'>{a['device']}</div><div style='font-size:11px;'>{a['reason']}</div></div>", unsafe_allow_html=True)
        else:
            st.info("System status: Optimal")

        # Audit Trail
        st.divider()
        st.subheader("🏥 Auditor Logs")
        if dashboard_data["audits"]:
            for au in dashboard_data["audits"][:5]:
                s = au.get('verification_status')
                c = "#2ecc71" if s == 'VERIFIED_OPTIMIZED' else "#e74c3c"
                st.markdown(f"<div style='padding:10px; border-left:4px solid {c}; background:rgba(255,255,255,0.03); margin-bottom:10px;'><div style='font-size:10px; font-weight:900; color:{c};'>{s}</div><div style='font-size:12px; font-weight:600;'>{au.get('device')}</div><div style='font-size:11px; opacity:0.7;'>{au.get('doctor_notes')}</div></div>", unsafe_allow_html=True)
        else:
            st.caption("No autonomous audits logged.")

        st.divider()
        st.subheader("Control Signals")
        signals = dashboard_data.get("control_signals", [])
        if signals:
            for sig in signals[:5]:
                status = sig.get("result", {}).get("status")
                st.code(f"{sig.get('device')} -> {sig.get('command')} [{status}]")
        else:
            st.caption("No machine bridge signals yet.")

    # 3. Diagnostic Tools
    st.divider()
    st.subheader("🧪 Advanced Diagnostic Tools")
    tab_chat, tab_studio = st.tabs(["💬 AI Expert Consultation", "🔬 Agent Prompt Lab"])
    
    with tab_chat:
        if "msgs" not in st.session_state: st.session_state.msgs = []
        
        # Fixed-height scrollable container for professional chat layouts
        chat_container = st.container(height=350)
        with chat_container:
            for m in st.session_state.msgs:
                with st.chat_message(m["role"]): st.markdown(m["content"])
                
        # Unique key prevents widget duplication on page state reruns
        if p := st.chat_input("Ask SustainAI expert...", key="expert_chat_input"):
            st.session_state.msgs.append({"role": "user", "content": p})
            with chat_container:
                with st.chat_message("user"): st.markdown(p)
            
            try:
                r = requests.post(f"{API_URL}/api/chat", json={"session_id": st.session_state["session_id"], "message": p})
                resp = r.json().get("response") if r.status_code == 200 else "AI Engine Busy."
            except Exception:
                resp = "Core Engine Offline."
                
            st.session_state.msgs.append({"role": "assistant", "content": resp})
            st.rerun()

    with tab_studio:
        agent_studio_panel(dashboard_data["logs"], {"session_id": st.session_state["session_id"]})

    # --- GLOBAL SYNC LOOP ---
    if st.session_state["live_mode"]:
        if st.session_state["analysis_in_progress"]:
            time.sleep(1) # Fast refresh during analysis
            st.rerun()
        else:
            time.sleep(5) # Steady refresh for dashboard
            st.rerun()

if __name__ == "__main__":
    run_dashboard()
