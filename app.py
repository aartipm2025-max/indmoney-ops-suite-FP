import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(
    page_title="INDmoney Investor Ops Suite",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_resource(show_spinner=False)
def _prewarm_smart_sync_kb() -> bool:
    """Preload KB retriever/reranker once per Streamlit server process."""
    from pillars.pillar_a_knowledge.answerer import prewarm_knowledge_base

    prewarm_knowledge_base()
    return True


_prewarm_smart_sync_kb()

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
</style>
""", unsafe_allow_html=True)

# Sidebar — System Health
with st.sidebar:
    st.image("https://www.indmoney.com/favicon.ico", width=40)
    st.title("Ops Suite")
    st.markdown("---")

    error_log = Path("logs/system_errors.log")

    if error_log.exists():
        import re

        content = error_log.read_text(encoding="utf-8", errors="ignore")

        # Split log into blocks
        blocks = re.split(r"─{20,}", content)

        total_pending = 0
        actionable = 0
        transient = 0

        transient_keywords = [
            "ratelimit", "rate_limit", "autherror",
            "authentication", "jsondecode", "invalid_api_key"
        ]

        for block in blocks:
            if "[STATUS]" not in block:
                continue

            status_match = re.search(r"\[STATUS\]\s+(\S+)", block)
            if not status_match:
                continue

            status = status_match.group(1).lower()

            # Ignore already handled logs
            if status in ["documented", "resolved"]:
                continue

            if status != "pending":
                continue

            total_pending += 1
            block_lower = block.lower()

            if any(kw in block_lower for kw in transient_keywords):
                transient += 1
            else:
                actionable += 1

        # Display system health
        if actionable > 0:
            st.warning(f"🟡 {actionable} actionable error{'s' if actionable != 1 else ''}")
        else:
            st.success("🟢 System healthy")

        # Expand log details
        if total_pending > 0:
            with st.expander(f"📋 Log: {total_pending} total pending"):
                st.caption(f"Actionable: {actionable}")
                st.caption(f"Transient (rate-limit/auth/json): {transient}")

    else:
        st.success("🟢 No errors logged")

    st.markdown("---")
    st.caption("INDmoney Investor Ops & Intelligence Suite")
    st.caption("Built by Aarti Dhavare")

# Main tabs
tab_a, tab_b, tab_c, tab_d = st.tabs([
    "📚 Smart-Sync KB",
    "📊 Pulse & Voice",
    "✅ HITL Center",
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