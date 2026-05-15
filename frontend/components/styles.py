import streamlit as st

def inject_styles():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Outfit:wght@400;700&display=swap');
            
            :root {
                --glass-bg: rgba(25, 25, 35, 0.65);
                --glass-border: rgba(255, 255, 255, 0.08);
                --accent-color: #2d9c6e;
                --text-secondary: #888;
            }

            .stApp {
                background-color: #0e1117;
                font-family: 'Inter', sans-serif;
            }

            h1, h2, h3 {
                font-family: 'Outfit', sans-serif !important;
                font-weight: 700 !important;
            }

            /* Glassmorphism containers */
            .glass-card {
                background: var(--glass-bg);
                backdrop-filter: blur(12px);
                border: 1px solid var(--glass-border);
                border-radius: 16px;
                padding: 24px;
                margin-bottom: 20px;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
                overflow: hidden; /* Fix out of box issues */
            }

            .stMarkdown div {
                overflow-wrap: break-word;
            }

            /* Metric styling */
            [data-testid="stMetricValue"] {
                font-family: 'Outfit', sans-serif;
                font-weight: 800;
                font-size: 2.2rem !important;
                color: #fff !important;
            }

            /* Badge styling */
            .badge {
                padding: 4px 10px;
                border-radius: 50px;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .badge-high { background: rgba(231, 76, 60, 0.15); color: #e74c3c; border: 1px solid rgba(231, 76, 60, 0.3); }
            .badge-medium { background: rgba(243, 156, 18, 0.15); color: #f39c12; border: 1px solid rgba(243, 156, 18, 0.3); }
            .badge-low { background: rgba(52, 152, 219, 0.15); color: #3498db; border: 1px solid rgba(52, 152, 219, 0.3); }

            /* Sidebar customization */
            section[data-testid="stSidebar"] {
                background-color: #11141a;
                border-right: 1px solid var(--glass-border);
            }

            /* Streamlit specific overrides */
            .stButton>button {
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.2s ease;
            }
            .stButton>button:hover {
                border-color: var(--accent-color);
                color: var(--accent-color);
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(45, 156, 110, 0.2);
            }
        </style>
    """, unsafe_allow_html=True)
