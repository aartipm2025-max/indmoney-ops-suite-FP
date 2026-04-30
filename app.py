from dotenv import load_dotenv
load_dotenv()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(
    page_title="INDmoney Investor Ops Suite",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# Custom CSS — INDmoney navy + gold theme
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; }
    .main .block-container { padding-top: 1rem; max-width: 1200px; }
    h1 { color: #0B1F3A; }
    h2, h3 { color: #0B1F3A; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #F6F8FB;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #0B1F3A;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0B1F3A;
        color: #D4A437;
    }
    .metric-card {
        background: #F6F8FB;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #D4A437;
        margin-bottom: 12px;
    }
    .source-tag {
        background: #E8F0FE;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.85em;
        color: #0B1F3A;
    }
    .chat-agent {
        background: #F6F8FB;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 4px solid #0B1F3A;
    }
    .chat-user {
        background: #E8F0FE;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 4px solid #4285F4;
        margin-left: 40px;
    }
</style>
""", unsafe_allow_html=True)

# Main tabs
tab_a, tab_b, tab_c, tab_d, tab_e = st.tabs([
    "💬 Ask About Funds",
    "📊 Weekly Pulse",
    "🎙️ Voice Scheduler",
    "✅ Action Approval",
    "📈 Evals"
])

with tab_a:
    from ui.tabs.tab_a import render_tab_a
    render_tab_a()

with tab_b:
    from ui.tabs.tab_b import render_tab_b
    render_tab_b()

with tab_c:
    from ui.tabs.tab_c import render_tab_c
    render_tab_c()

with tab_d:
    from ui.tabs.tab_d import render_tab_d
    render_tab_d()

with tab_e:
    from ui.tabs.tab_e import render_tab_e
    render_tab_e()

st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 20px; color: #5A6C7D;">
    <p style="margin: 0; font-size: 0.9em;"><strong>INDmoney Investor Ops & Intelligence Suite</strong></p>
    <p style="margin: 0; font-size: 0.8em;">Built by Aarti Dhavare</p>
</div>
""", unsafe_allow_html=True)