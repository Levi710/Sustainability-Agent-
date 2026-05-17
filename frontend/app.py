import streamlit as st
import os
import sys

# Add current dir to path for absolute imports
sys.path.append(os.path.dirname(__file__))

from utils import init_state, set_page

# Must be first call
st.set_page_config(page_title="SustainAI Studio", layout="wide")

# Initialize
init_state()

st.sidebar.title("🌍 SustainAI Studio")
st.sidebar.info("Navigate to the Dashboard to begin.")

# Main content
col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("<h1 style='font-size: 3.5rem;'>SustainAI</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #2d9c6e;'>Multi-Agent Energy Intelligence</h3>", unsafe_allow_html=True)
    if st.button("🚀 Enter Dashboard"):
        set_page("Dashboard")

with col2:
    st.image("https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?auto=format&fit=crop&q=80&w=2070")
