import os
import sys
import time
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import API_URL, init_state, set_page

st.set_page_config(page_title="Telemetry Automator", page_icon="⚡", layout="wide")
init_state()
set_page("Telemetry")

# 1. State Guard
if not st.session_state.get("session_id"):
    st.warning("No active session. Please configure a building profile in the Dashboard first.")
    if st.button("Go to Dashboard"):
        set_page("Dashboard")
    st.stop()

session_id = st.session_state["session_id"]

# 2. Universal Premium CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@300;400;600&display=swap');
.stApp { background-color: #0f111a; color: #f1f5f9; font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Outfit', sans-serif; font-weight: 800; letter-spacing: -0.5px; }
.glass-card { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 20px; margin-bottom: 15px; }
.heartbeat { animation: pulse 1.5s infinite; color: #2ecc71; font-weight: 800; font-size: 0.85rem; letter-spacing: 1px; }
@keyframes pulse { 0% { opacity: 0.3; } 50% { opacity: 1; } 100% { opacity: 0.3; } }
</style>
""", unsafe_allow_html=True)

# 3. Synchronize Backend persistent stream status
fleet_streaming = False
try:
    status_res = requests.get(f"{API_URL}/telemetry/status/{session_id}", timeout=5)
    if status_res.status_code == 200:
        fleet_streaming = status_res.json().get("is_running", False)
except Exception:
    pass

st.title("⚡ Autonomous Infrastructure Telemetry")
st.caption("Runs a persistent background fleet simulation on the FastAPI Core. You do not need to keep this tab open!")

col_cfg, col_status = st.columns([1, 1])

with col_cfg:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("🛠️ Persistent Fleet Stream Controls")
    interval = st.number_input("Fleet poll interval (seconds)", value=10, min_value=5, max_value=60)
    
    st.caption("The persistent scheduler runs securely in the backend process using hardware-accurate metrics.")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 Start Persistent Stream", use_container_width=True, disabled=fleet_streaming):
            try:
                b_type = st.session_state.get("building_profile", {}).get("building_type", "commercial_firm")
                start_res = requests.post(f"{API_URL}/telemetry/start?session_id={session_id}&building_type={b_type}&interval_seconds={int(interval)}")
                if start_res.status_code == 200:
                    st.success("Persistent telemetry engine started!")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to start persistent stream: {e}")
    with c2:
        if st.button("🛑 Stop Stream", use_container_width=True, disabled=not fleet_streaming):
            try:
                stop_res = requests.post(f"{API_URL}/telemetry/stop?session_id={session_id}")
                if stop_res.status_code == 200:
                    st.info("Persistent telemetry engine stopped.")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to stop persistent stream: {e}")
                
    st.markdown("</div>", unsafe_allow_html=True)

with col_status:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("📡 Engine Stream Status")
    
    if fleet_streaming:
        st.markdown("<div class='heartbeat'>● SIMULATOR ACTIVE & RUNNING IN BACKGROUND</div>", unsafe_allow_html=True)
        st.success(f"Stream Status: ACTIVE (Every {interval}s)")
    else:
        st.info("Stream Status: STOPPED / READY")
        
    # Fetch latest telemetry data to display metrics
    db_events = []
    try:
        events_res = requests.get(f"{API_URL}/telemetry/events/{session_id}?limit=50", timeout=5)
        if events_res.status_code == 200:
            db_events = events_res.json()
    except Exception:
        pass
        
    if db_events:
        anoms = sum(1 for e in db_events if e.get("event_type") in ["surveillance_anomaly", "hardware_malfunction", "occupancy_triggered_spike"])
        offline = sum(1 for e in db_events if e.get("event_type") == "not_responding")
        
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Total Telemetry Ticks", len(db_events))
        with m2:
            st.metric("Detected Spikes / Anomalies", anoms)
    else:
        st.caption("Awaiting first telemetry events...")
    st.markdown("</div>", unsafe_allow_html=True)

# 4. Manual Debugging Single Poll
st.divider()
st.subheader("🔬 Single Fleet Poll (Manual Override)")
col_p1, col_p2 = st.columns([2, 1])
with col_p1:
    st.caption("Force one simulated snapshot immediately into the telemetry stream to test agent behaviour.")
with col_p2:
    if st.button("⚡ Trigger Manual Snapshot", use_container_width=True):
        try:
            res = requests.post(f"{API_URL}/telemetry/surveillance-snapshot", json={"session_id": session_id, "force_anomaly": True}, timeout=15)
            if res.status_code == 200:
                st.toast("Manual snapshot successfully injected!", icon="⚡")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"Manual poll failed: {e}")

# 5. Live Telemetry Stream Grid
st.divider()
st.subheader("📡 Live Fleet Telemetry Stream (From Database)")

if db_events:
    df = pd.DataFrame(db_events)
    # Format and present beautifully
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%H:%M:%S")
    df = df.rename(columns={
        "device": "Device ID",
        "timestamp": "Timestamp",
        "kwh": "Energy Usage (kWh)",
        "event_type": "Stream Event Type"
    })
    st.dataframe(
        df[["Timestamp", "Device ID", "Energy Usage (kWh)", "Stream Event Type"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No telemetry logs found for this session. Start the persistent stream above to generate live data.")

# 6. Auto-Refresh Loop if Streaming is Active
if fleet_streaming:
    time.sleep(3) # Non-blocking fast refresh for telemetry data stream
    st.rerun()
