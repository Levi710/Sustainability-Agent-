import streamlit as st
import requests
import pandas as pd
import textwrap
from components.styles import inject_styles
from components.charts import usage_heatmap, anomaly_chart

st.set_page_config(page_title="Device Insights", page_icon="🔌", layout="wide")
inject_styles()

API_URL = "http://127.0.0.1:8000/api"

st.markdown('<h1 style="margin-bottom:0;">Anomaly Detection Engine</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#888; margin-bottom:20px;">Detailed inspection of device-level consumption and detected anomalies.</p>', unsafe_allow_html=True)

if not st.session_state.get("session_id"):
    st.warning("No active session. Please go to the Dashboard.")
else:
    # Get all device data for charts
    if "df" in st.session_state and st.session_state.df is not None:
        df = pd.DataFrame(st.session_state.df)
        devices = df["device"].unique()
        
        selected_device = st.selectbox("Select Device for Analysis", devices)
        
        col_charts, col_anom = st.columns([2, 1])
        
        with col_charts:
            st.markdown(f"### {selected_device} Usage Analysis")
            tab1, tab2 = st.tabs(["🔥 Heatmap", "📈 Anomaly Chart"])
            
            with tab1:
                fig_heat = usage_heatmap(df, selected_device)
                st.plotly_chart(fig_heat, use_container_width=True)
            
            with tab2:
                # Get anomalies for this device
                res = requests.get(f"{API_URL}/anomalies/{st.session_state['session_id']}")
                anoms = res.json() if res.status_code == 200 else []
                device_anoms = [a for a in anoms if a["device"] == selected_device]
                
                # Mock current kwh for anomaly markers if not in anom data
                for a in device_anoms:
                    if "kwh" not in a:
                        a["kwh"] = df[(df["device"] == a["device"]) & (df["timestamp"] == a["timestamp"])]["kwh"].values[0] if not df[(df["device"] == a["device"]) & (df["timestamp"] == a["timestamp"])].empty else 0

                fig_anom = anomaly_chart(df[df["device"] == selected_device], device_anoms)
                st.plotly_chart(fig_anom, use_container_width=True)

        with col_anom:
            st.markdown("### 🚨 Detected Anomalies")
            if st.button("Refresh Anomalies"):
                st.rerun()
                
            res = requests.get(f"{API_URL}/anomalies/{st.session_state['session_id']}")
            if res.status_code == 200:
                anomalies = res.json()
                if not anomalies:
                    st.info("No anomalies detected yet.")
                else:
                    # Show top 4
                    for a in anomalies[:4]:
                        severity_class = f"badge-{a['severity'].lower()}"
                        crit_badge = '<span class="badge" style="background:rgba(231,76,60,0.2); color:#e74c3c; margin-left:5px;">CRITICAL</span>' if a["is_critical_device"] else ""
                        color = '#e74c3c' if a['severity'] == 'high' else '#f39c12' if a['severity'] == 'medium' else '#3498db'
                        
                        st.markdown(f"""<div class="glass-card" style="padding: 15px; margin-bottom: 10px; border-left: 4px solid {color};">
<div style="display:flex; justify-content:space-between; align-items:center;">
<h5 style="margin:0;">{a['device']}</h5>
<span class="badge {severity_class}">{a['severity'].upper()}</span>
</div>
{crit_badge}
<p style="margin: 8px 0 0 0; font-size: 12px; color: #aaa;"><b>Time:</b> {a['timestamp']}</p>
<p style="margin: 4px 0 0 0; font-size: 13px;">{a['reason']}</p>
</div>""", unsafe_allow_html=True)

                    if len(anomalies) > 4:
                        with st.expander(f"View {len(anomalies)-4} More Records"):
                            for a in anomalies[4:]:
                                severity_class = f"badge-{a['severity'].lower()}"
                                crit_badge = '<span class="badge" style="background:rgba(231,76,60,0.2); color:#e74c3c; margin-left:5px;">CRITICAL</span>' if a["is_critical_device"] else ""
                                color = '#e74c3c' if a['severity'] == 'high' else '#f39c12' if a['severity'] == 'medium' else '#3498db'
                                st.markdown(f"""<div class="glass-card" style="padding: 15px; margin-bottom: 10px; border-left: 4px solid {color};">
<div style="display:flex; justify-content:space-between; align-items:center;">
<h5 style="margin:0;">{a['device']}</h5>
<span class="badge {severity_class}">{a['severity'].upper()}</span>
</div>
{crit_badge}
<p style="margin: 8px 0 0 0; font-size: 12px; color: #aaa;"><b>Time:</b> {a['timestamp']}</p>
<p style="margin: 4px 0 0 0; font-size: 13px;">{a['reason']}</p>
</div>""", unsafe_allow_html=True)
    else:
        st.info("Please upload data on the Dashboard to see device-level insights.")
