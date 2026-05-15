import streamlit as st
from components.styles import inject_styles

st.set_page_config(
    page_title="SustainAI V2",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_styles()

if "session_id" not in st.session_state:
    st.session_state["session_id"] = None
if "building_profile" not in st.session_state:
    st.session_state["building_profile"] = None
if "analysis_complete" not in st.session_state:
    st.session_state["analysis_complete"] = False

st.sidebar.title("🌍 SustainAI V2")
st.sidebar.markdown("---")
st.sidebar.info("Navigate through the pages above to configure your building profile, analyze energy data, and view real-time telemetry simulation.")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
        <div style="margin-top: 40px;">
            <h1 style="font-size: 3.5rem; margin-bottom: 0;">SustainAI</h1>
            <h3 style="color: #2d9c6e; font-weight: 400; margin-top: 0;">Multi-Agent Energy Intelligence</h3>
            <p style="font-size: 1.2rem; color: #888; max-width: 600px; line-height: 1.6;">
                Welcome to the V2 reasoning engine. We combine multi-agent orchestration 
                with real-time IoT telemetry to provide actionable sustainability paths 
                for your enterprise.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button("🚀 Get Started", use_container_width=True):
        st.info("Select **Dashboard** in the sidebar to begin.")

with col2:
    st.markdown("""
        <div class="glass-card" style="margin-top: 40px; text-align: center;">
            <h2 style="margin: 0;">V2 Build</h2>
            <div style="font-size: 4rem; margin: 20px 0;">🛡️</div>
            <p style="font-size: 0.9rem; color: #aaa;">
                Constraint-First Reasoning<br>
                Zero-PII Local Processing<br>
                Real-time Anomaly Detection
            </p>
        </div>
    """, unsafe_allow_html=True)
