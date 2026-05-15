import streamlit as st
import requests

st.set_page_config(page_title="Telemetry Automator", page_icon="⚡", layout="wide")
API_URL = "http://127.0.0.1:8000/api"

st.title("Real-Time Telemetry & Auto-Analysis")
st.write("This simulator streams live IoT data and triggers the reasoning agent automatically upon anomaly detection.")

if not st.session_state.get("session_id"):
    st.warning("No active session. Please configure building profile in the Dashboard.")
else:
    col1, col2 = st.columns(2)
    with col1:
        interval = st.number_input("Telemetry Tick Interval (seconds)", value=5, min_value=2)
        if st.button("Start Telemetry Loop"):
            res = requests.post(f"{API_URL}/telemetry/start", params={
                "session_id": st.session_state["session_id"],
                "building_type": st.session_state["building_profile"]["building_type"],
                "interval_seconds": interval
            })
            if res.status_code == 200:
                st.success("Telemetry Started!")
    with col2:
        st.write("")
        st.write("")
        if st.button("Stop Telemetry"):
            requests.post(f"{API_URL}/telemetry/stop", params={"session_id": st.session_state["session_id"]})
            st.success("Telemetry Stopped.")

    st.divider()
    
    # Live Monitoring Toggle
    live_mode = st.sidebar.checkbox("📡 Live Monitoring Mode", value=True)
    if live_mode:
        st.sidebar.info("UI is auto-refreshing every 4s to show live I/O flow.")
        
    col_ev, col_cmd = st.columns([1, 1])
    
    with col_ev:
        st.subheader("📡 Live Events View")
        ev_res = requests.get(f"{API_URL}/telemetry/events/{st.session_state['session_id']}", params={"limit": 15})
        if ev_res.status_code == 200:
            events = ev_res.json()
            if events:
                for e in events:
                    emoji = "🔥" if e["event_type"] == "spike" else "💡" if e["event_type"] == "idle_drain" else "📉" if "voice" in e["event_type"] else "✅"
                    sensor_info = f" | 🎙️ {e['sensor']}" if e.get('sensor') else ""
                    st.write(f"{emoji} **{e['device']}** - {e['kwh']} kWh - *{e['event_type']}*{sensor_info}")
            else:
                with st.spinner("Synchronizing with IoT sensors..."):
                    st.info("Waiting for telemetry data...")

    with col_cmd:
        st.subheader("🛡️ Autonomous Control Center")
        st.caption("Live feed of AI-issued IoT commands for grid stabilization.")
        recs_res = requests.get(f"{API_URL}/recommendations/{st.session_state['session_id']}")
        if recs_res.status_code == 200:
            auto_recs = [r for r in recs_res.json() if r.get('triggered_by') == 'telemetry_auto']
            if auto_recs:
                for ar in reversed(auto_recs[-5:]): # Show latest first
                    st.markdown(f"""<div style="background: rgba(45,156,110,0.1); padding: 10px; border-radius: 8px; border-left: 4px solid #2d9c6e; margin-bottom: 8px;">
<div style="font-size: 10px; color: #2d9c6e; font-weight: bold; letter-spacing: 1px;">WORKER DISPATCHED</div>
<div style="font-size: 14px; font-weight: 600; color: #eee; margin: 4px 0;">{ar['issue']}</div>
<code style="font-size: 11px; background: #111; padding: 2px 6px; border-radius: 4px; color: #0f0;">FIX: {ar.get('control_action', 'SET_STATE:STABLE')}</code>
</div>""", unsafe_allow_html=True)
            else:
                st.info("No autonomous commands issued yet. Grid is currently stable.")
        
        st.divider()
        st.subheader("🏥 Verification Audit")
        st.caption("The 'Doctor Agent' auditing fix effectiveness via post-action telemetry.")
        
        # In a real app we'd fetch doctor_audits from a specific endpoint, 
        # but for now we'll simulate the live audit based on the latest reasoning state.
        audit_res = requests.get(f"{API_URL}/data/{st.session_state['session_id']}")
        if audit_res.status_code == 200:
            audit_data = audit_res.json()
            audits = audit_data.get("doctor_audits", [])
            if audits:
                for audit in reversed(audits[-5:]):
                    status = audit.get('verification_status', 'PENDING')
                    color = "#2d9c6e" if "VERIFIED" in status else "#f39c12" if "SUPERFICIAL" in status else "#e74c3c"
                    st.markdown(f"""<div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px; border-left: 4px solid {color}; margin-bottom: 8px;">
<div style="font-size: 10px; color: {color}; font-weight: bold; letter-spacing: 1px;">DOCTOR SIGN-OFF: {status}</div>
<div style="font-size: 13px; color: #eee; margin: 4px 0;">{audit.get('device')} - {audit.get('doctor_notes')}</div>
<div style="font-size: 11px; color: #888;">Optimization Score: {audit.get('optimization_score', 0)*100:.1f}%</div>
</div>""", unsafe_allow_html=True)
            else:
                st.info("Awaiting post-fix telemetry for audit...")

    # Auto-refresh loop
    if live_mode:
        import time
        time.sleep(4)
        st.rerun()
