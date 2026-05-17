import os

import streamlit as st

API_BASE_URL = os.getenv("SUSTAINAI_API_URL", "http://localhost:8000").rstrip("/")
API_URL = f"{API_BASE_URL}/api"

def init_state():
    """Ensures all required session state keys exist."""
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Home"
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = None
    if "building_profile" not in st.session_state:
        st.session_state["building_profile"] = None
    if "analysis_complete" not in st.session_state:
        st.session_state["analysis_complete"] = False
    if "live_mode_active" not in st.session_state:
        st.session_state["live_mode_active"] = False

def set_page(name):
    """Sets the current page and handles session logic."""
    init_state() # Ensure keys exist
    
    if st.session_state["current_page"] != name:
        st.session_state["live_mode_active"] = False # Stop sync on switch
        st.session_state["current_page"] = name
        st.rerun()
