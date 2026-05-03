from dotenv import load_dotenv
load_dotenv()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="INDmoney Investor Ops Suite",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Session State ─────────────────────────────────────────────────────────────
for _k, _v in [
    ("authenticated", False),
    ("username", ""),
    ("email", ""),
    ("sidebar_nav", "Home"),
    ("queries_this_session", 0),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Production design system — INDmoney B2B Fintech ─────────────────────────
st.markdown("""
<style>
/* ── Reset & Base ─────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
.stApp {
    background-color: #F6F8FB;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
}
.main .block-container {
    padding-top: 1rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* ── Brand Header ─────────────────────────────────────────────────────────── */
.brand-header {
    background: #0B1F3A;
    padding: 0 28px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-radius: 8px;
    margin-bottom: 8px;
    box-shadow: 0 2px 12px rgba(11,31,58,0.2);
}
.brand-title {
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.01em;
}
.brand-sub {
    color: #D4A437;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.02em;
}

/* ── Sidebar ──────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: #0B1F3A !important;
    border-right: 1px solid rgba(255,255,255,0.07) !important;
}
section[data-testid="stSidebar"] > div {
    background-color: #0B1F3A !important;
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div { color: rgba(255,255,255,0.75); }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #FFFFFF; }
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.1) !important;
}
/* Nav radio items */
section[data-testid="stSidebar"] .stRadio label {
    color: rgba(255,255,255,0.65) !important;
    font-size: 13px !important;
    padding: 7px 4px !important;
    cursor: pointer;
    transition: color 0.15s ease;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has([aria-checked="true"]) label {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}
/* Sidebar sign-out button */
section[data-testid="stSidebar"] .stButton > button:not([kind="primary"]) {
    background: rgba(255,255,255,0.06) !important;
    color: rgba(255,255,255,0.6) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    margin-top: 4px;
}
section[data-testid="stSidebar"] .stButton > button:not([kind="primary"]):hover {
    background: rgba(255,255,255,0.12) !important;
    color: #FFFFFF !important;
    border-color: rgba(255,255,255,0.38) !important;
    box-shadow: none !important;
}

/* ── Typography ───────────────────────────────────────────────────────────── */
h1 { color: #0B1F3A; font-weight: 700; font-size: 22px; line-height: 1.3;
     margin-bottom: 4px; letter-spacing: -0.01em; }
h2 { color: #0B1F3A; font-weight: 600; font-size: 18px; line-height: 1.4; }
h3 { color: #0B1F3A; font-weight: 600; font-size: 15px; line-height: 1.4; }
p, li { color: #2C3E50; font-size: 14px; line-height: 1.6; }

/* ── Cards ────────────────────────────────────────────────────────────────── */
.card {
    background: #FFFFFF; border-radius: 8px; padding: 24px;
    border: 1px solid #E8EDF3; box-shadow: 0 1px 3px rgba(11,31,58,0.06);
    margin-bottom: 16px; transition: box-shadow 0.2s ease;
}
.card:hover { box-shadow: 0 4px 12px rgba(11,31,58,0.1); }
.card-gold {
    background: #FFFFFF; border-radius: 8px; padding: 24px;
    border: 1px solid #E8EDF3; border-left: 4px solid #D4A437;
    box-shadow: 0 1px 3px rgba(11,31,58,0.06); margin-bottom: 16px;
    transition: box-shadow 0.2s ease;
}
.card-gold:hover { box-shadow: 0 4px 12px rgba(11,31,58,0.1); }
.card-navy {
    background: #FFFFFF; border-radius: 8px; padding: 24px;
    border: 1px solid #E8EDF3; border-left: 4px solid #0B1F3A;
    box-shadow: 0 1px 3px rgba(11,31,58,0.06); margin-bottom: 16px;
}
.card-green {
    background: #FFFFFF; border-radius: 8px; padding: 24px;
    border: 1px solid #E8EDF3; border-left: 4px solid #10B981;
    box-shadow: 0 1px 3px rgba(11,31,58,0.06); margin-bottom: 16px;
}
.card-blue {
    background: #FFFFFF; border-radius: 8px; padding: 24px;
    border: 1px solid #E8EDF3; border-left: 4px solid #3B82F6;
    box-shadow: 0 1px 3px rgba(11,31,58,0.06); margin-bottom: 16px;
}
.metric-card {
    background: #FFFFFF; border-radius: 8px; padding: 18px 20px;
    border: 1px solid #E8EDF3; border-left: 4px solid #D4A437;
    box-shadow: 0 1px 3px rgba(11,31,58,0.06); margin-bottom: 12px;
    transition: box-shadow 0.2s ease;
}
.metric-card:hover { box-shadow: 0 4px 12px rgba(11,31,58,0.1); }

.answer-bullet {
    background: #FFFFFF; border-radius: 8px; padding: 16px 20px;
    border: 1px solid #E8EDF3; border-left: 4px solid #D4A437;
    box-shadow: 0 1px 2px rgba(11,31,58,0.04); margin-bottom: 10px;
    transition: box-shadow 0.2s ease;
}
.answer-bullet:hover { box-shadow: 0 4px 10px rgba(11,31,58,0.08); }

.hitl-op-card {
    background: #FFFFFF; border-radius: 8px; padding: 24px;
    border: 1px solid #E8EDF3; border-left: 4px solid #D4A437;
    box-shadow: 0 1px 3px rgba(11,31,58,0.06); margin-bottom: 16px;
}

/* ── Eval Summary Cards ───────────────────────────────────────────────────── */
.eval-card {
    background: #FFFFFF; border-radius: 8px; padding: 24px 20px;
    border: 1px solid #E8EDF3; box-shadow: 0 1px 3px rgba(11,31,58,0.06);
    text-align: center; transition: box-shadow 0.2s ease;
}
.eval-card:hover { box-shadow: 0 4px 12px rgba(11,31,58,0.1); }
.eval-label {
    font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #8A9BB0; margin-bottom: 12px;
}
.eval-score {
    font-size: 36px; font-weight: 700; color: #0B1F3A;
    line-height: 1; margin-bottom: 6px; font-variant-numeric: tabular-nums;
}
.eval-pct { font-size: 13px; color: #5A6C7D; margin-bottom: 12px; font-weight: 500; }
.eval-bar {
    height: 4px; border-radius: 2px; background: #F0F3F6;
    margin: 10px 0 14px 0; overflow: hidden;
}
.eval-bar-fill { height: 100%; border-radius: 2px; }

/* ── Example Query Chips ──────────────────────────────────────────────────── */
.chip-container { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 24px 0; }
.chip {
    display: inline-block; background: #FFFFFF;
    border: 1px solid #E8EDF3; border-radius: 20px;
    padding: 6px 14px; font-size: 12px; color: #5A6C7D;
    transition: border-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
    cursor: default; white-space: nowrap;
}
.chip:hover {
    border-color: #D4A437; color: #0B1F3A;
    box-shadow: 0 0 0 2px rgba(212,164,55,0.12);
}

/* ── Route Badges ─────────────────────────────────────────────────────────── */
.route-badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;
}
.route-fact_only { background: #DBEAFE; color: #1E40AF; }
.route-fee_only  { background: #EDE9FE; color: #5B21B6; }
.route-both      { background: #FEF3C7; color: #92400E; }
.route-default   { background: #F3F4F6; color: #374151; }

/* ── Status Badges ────────────────────────────────────────────────────────── */
.status-pass {
    background: #D1FAE5; color: #065F46; padding: 3px 10px; border-radius: 20px;
    font-size: 0.72em; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}
.status-pending {
    background: #FEF3C7; color: #92400E; padding: 3px 10px; border-radius: 20px;
    font-size: 0.72em; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}
.status-fail {
    background: #FEE2E2; color: #991B1B; padding: 3px 10px; border-radius: 20px;
    font-size: 0.72em; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}
.status-approved {
    background: #DBEAFE; color: #1E40AF; padding: 3px 10px; border-radius: 20px;
    font-size: 0.72em; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}
.status-rejected {
    background: #F3F4F6; color: #374151; padding: 3px 10px; border-radius: 20px;
    font-size: 0.72em; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}

/* ── Source Tags ──────────────────────────────────────────────────────────── */
.source-tag {
    background: #EEF2FF; padding: 3px 10px; border-radius: 4px;
    font-size: 0.8em; color: #3730A3; font-weight: 500;
    border: 1px solid #C7D2FE; display: inline-block; margin: 2px 3px;
}

/* ── Section Labels ───────────────────────────────────────────────────────── */
.section-label {
    font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #8A9BB0;
    margin: 0 0 16px 0; padding-bottom: 8px;
    border-bottom: 1px solid #F0F3F6;
}

/* ── Chat Bubbles ─────────────────────────────────────────────────────────── */
.chat-agent {
    background: #FFFFFF; border-radius: 2px 12px 12px 12px;
    padding: 14px 18px; margin-bottom: 12px;
    border: 1px solid #E8EDF3; max-width: 88%;
    box-shadow: 0 1px 3px rgba(11,31,58,0.05);
}
.chat-user {
    background: #EEF2FF; border-radius: 12px 2px 12px 12px;
    padding: 14px 18px; margin-bottom: 12px; margin-left: auto;
    max-width: 88%; border: 1px solid #C7D2FE;
    box-shadow: 0 1px 3px rgba(11,31,58,0.05);
}

/* ── State Indicator ──────────────────────────────────────────────────────── */
.state-indicator {
    background: #F6F8FB; border: 1px solid #E8EDF3;
    border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;
    display: flex; align-items: center; justify-content: space-between;
}
.state-name {
    font-size: 12px; font-weight: 700; color: #0B1F3A;
    letter-spacing: 0.06em; text-transform: uppercase;
}

/* ── Empty State ──────────────────────────────────────────────────────────── */
.empty-state {
    text-align: center; padding: 48px 24px;
    background: #FFFFFF; border-radius: 8px; border: 1px solid #E8EDF3;
}
.empty-state-icon { font-size: 2.2em; margin-bottom: 12px; }
.empty-state h3 { color: #0B1F3A; margin: 8px 0; font-size: 1.05em; }
.empty-state p { color: #5A6C7D; margin: 0; font-size: 0.88em; }

/* ── Streamlit Overrides ──────────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #FFFFFF; border: 1px solid #E8EDF3;
    border-radius: 8px; padding: 16px 20px;
    box-shadow: 0 1px 2px rgba(11,31,58,0.04);
    transition: box-shadow 0.2s ease;
}
[data-testid="metric-container"]:hover { box-shadow: 0 4px 10px rgba(11,31,58,0.08); }

.stButton > button {
    border-radius: 6px; font-weight: 500; font-size: 13px;
    padding: 10px 20px; transition: all 0.2s ease;
}
.stButton > button[kind="primary"] {
    background-color: #0B1F3A; color: #FFFFFF; border: 1px solid #0B1F3A;
}
.stButton > button[kind="primary"]:hover {
    background-color: #162D4F; border-color: #D4A437;
    box-shadow: 0 4px 12px rgba(11,31,58,0.2);
}
.stButton > button[kind="primary"]:active { transform: scale(0.98); }
.stButton > button:not([kind="primary"]) {
    background-color: #FFFFFF; color: #0B1F3A; border: 1px solid #D4A437;
}
.stButton > button:not([kind="primary"]):hover {
    background-color: #FFF8EC; box-shadow: 0 2px 8px rgba(212,164,55,0.2);
}
.stButton > button:not([kind="primary"]):active { transform: scale(0.98); }

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border: 1.5px solid #E8EDF3; border-radius: 6px;
    font-size: 14px; color: #2C3E50; background: #FFFFFF;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #D4A437; box-shadow: 0 0 0 3px rgba(212,164,55,0.12);
}
.stSelectbox > div > div { border: 1.5px solid #E8EDF3; border-radius: 6px; }

.stAlert { border-radius: 6px; font-size: 13px; }
hr { border: none; border-top: 1px solid #E8EDF3; margin: 24px 0; }

/* Thin scrollbars */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #F6F8FB; }
::-webkit-scrollbar-thumb { background: #D1D9E0; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #B0BEC5; }
</style>
""", unsafe_allow_html=True)

# ── Landing Page ──────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display: none !important; }
    .stApp {
        background: linear-gradient(180deg, #0B1F3A 0%, #1a2f4a 100%) !important;
    }
    .main .block-container {
        max-width: 320px !important;
        padding-top: 64px !important;
        padding-left: 12px !important;
        padding-right: 12px !important;
    }
    /* Compact form inputs */
    .stTextInput > div > div > input {
        height: 44px !important;
        font-size: 14px !important;
    }
    .stTextInput { margin-bottom: 12px !important; }
    /* Blue submit button — override global navy rule.
       Safe: this block only renders on the unauthenticated landing page. */
    [data-testid="stForm"] .stButton > button,
    [data-testid="stFormSubmitButton"] > button {
        background-color: #4285F4 !important;
        border-color: #4285F4 !important;
        color: #FFFFFF !important;
        font-weight: 500 !important;
        height: 44px !important;
        font-size: 14px !important;
        border-radius: 6px !important;
    }
    [data-testid="stForm"] .stButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        background-color: #357AE8 !important;
        border-color: #357AE8 !important;
        box-shadow: 0 4px 14px rgba(66,133,244,0.4) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center; margin-bottom: 40px;">
        <div style="font-size: 32px; font-weight: 700; color: #FFFFFF;
             letter-spacing: -0.02em; line-height: 1.1;
             display: inline-block; padding-bottom: 8px;
             border-bottom: 3px solid #D4A437;">
            INDmoney Investor Ops
        </div>
        <div style="max-width: 600px; margin: 24px auto 0 auto;
             font-size: 16px; color: rgba(255,255,255,0.9);
             font-weight: 400; line-height: 1.6; text-align: center;">
            Unified intelligence platform for fintech operations<br>
            RAG-powered knowledge base &nbsp;•&nbsp; AI sentiment analysis &nbsp;•&nbsp; Voice automation<br>
            Human-in-the-loop workflow orchestration
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(
            '<div style="padding: 0 0 4px 0; font-size: 14px; font-weight: 600; color: #0B1F3A;">Sign In</div>',
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            name_input = st.text_input("Username", placeholder="Enter your name")
            email_input = st.text_input("Email", placeholder="you@indmoney.com")
            submitted = st.form_submit_button(
                "Access Dashboard",
                use_container_width=True,
                type="primary",
            )
            if submitted:
                if name_input.strip() and email_input.strip():
                    st.session_state.authenticated = True
                    st.session_state.username = name_input.strip()
                    st.session_state.email = email_input.strip()
                    st.rerun()
                else:
                    st.error("Please enter both username and email address.")

    st.markdown("""
    <div style="text-align: center; margin-top: 32px;
         font-size: 12px; color: rgba(255,255,255,0.6);">
        Capstone Project 2026
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# ── Programmatic navigation (from Home quick-action buttons) ─────────────────
if "nav_goto" in st.session_state:
    st.session_state.sidebar_nav = st.session_state["nav_goto"]
    del st.session_state["nav_goto"]

# ── Sidebar ───────────────────────────────────────────────────────────────────
_NAV_ITEMS = [
    "Home",
    "Knowledge Base",
    "Weekly Pulse",
    "Voice Scheduler",
    "Action Approval",
    "Evaluation",
]

with st.sidebar:
    st.markdown("""
    <div style="padding: 24px 20px;
         border-bottom: 1px solid #D4A437; margin-bottom: 16px;">
        <div style="font-size: 18px; font-weight: 600; color: #FFFFFF;
             letter-spacing: -0.01em; line-height: 1.1;">
            INDmoney Ops
        </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        _NAV_ITEMS,
        key="sidebar_nav",
        label_visibility="collapsed",
    )

    st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown(
        f"""
        <div style="padding: 6px 0 10px 0;">
            <div style="font-size: 13px; font-weight: 600; color: #FFFFFF;
                 white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {st.session_state.username}
            </div>
            <div style="font-size: 11px; color: rgba(255,255,255,0.42);
                 margin-top: 2px; white-space: nowrap; overflow: hidden;
                 text-overflow: ellipsis;">
                {st.session_state.email}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Sign Out", use_container_width=True):
        for _k in ("authenticated", "username", "email", "sidebar_nav",
                   "queries_this_session", "pulse", "booking_context",
                   "submitted_bookings", "voice_state"):
            st.session_state.pop(_k, None)
        st.rerun()


# ── Home Dashboard ────────────────────────────────────────────────────────────
def render_home():
    import json

    # Prewarm models once per session — fires silently via @st.cache_resource;
    # shows spinner on Home (first load) rather than mid-query on Knowledge Base.
    if not st.session_state.get("_models_prewarmed"):
        from pillars.pillar_a_knowledge.answerer import prewarm_knowledge_base
        prewarm_knowledge_base()
        st.session_state["_models_prewarmed"] = True

    st.markdown(f"""
    <div class="brand-header">
        <span class="brand-title">Welcome back, {st.session_state.username}</span>
        <span class="brand-sub">{datetime.now().strftime("%A, %d %b %Y")}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label" style="margin-top: 24px;">Dashboard</div>',
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        try:
            from pillars.pillar_c_hitl.approval import get_pending_ops
            pending_count = len(get_pending_ops())
        except Exception:
            pending_count = 0
        accent = "#D4A437" if pending_count > 0 else "#10B981"
        note = "Requires attention" if pending_count > 0 else "All caught up"
        st.markdown(f"""
<div class="metric-card" style="border-left-color: {accent};">
    <div class="eval-label">Pending Approvals</div>
    <div style="font-size: 34px; font-weight: 700; color: #0B1F3A;
         line-height: 1; margin-bottom: 6px;">{pending_count}</div>
    <div style="font-size: 12px; color: #5A6C7D;">{note}</div>
</div>
""", unsafe_allow_html=True)

    with c2:
        rag_path = Path("evals/rag_eval_results.json")
        safety_path = Path("evals/safety_eval_results.json")
        if rag_path.exists() and safety_path.exists():
            try:
                rag_data = json.loads(rag_path.read_text())
                safety_data = json.loads(safety_path.read_text())
                rag_pct = (
                    sum(1 for r in rag_data if r["status"] == "pass")
                    / len(rag_data) * 100
                ) if rag_data else 0
                safety_ok = all(r["status"] == "pass" for r in safety_data)
                overall = "PASS" if rag_pct >= 70 and safety_ok else "REVIEW"
                accent2 = "#10B981" if overall == "PASS" else "#D4A437"
                sublabel = f"RAG {rag_pct:.0f}%  ·  Safety {'100%' if safety_ok else 'FAIL'}"
            except Exception:
                overall, accent2, sublabel = "ERROR", "#EF4444", "Could not parse results"
        else:
            overall, accent2, sublabel = "NOT RUN", "#8A9BB0", "Run evals to see results"
        st.markdown(f"""
<div class="metric-card" style="border-left-color: {accent2};">
    <div class="eval-label">Eval Status</div>
    <div style="font-size: 22px; font-weight: 700; color: #0B1F3A;
         line-height: 1; margin-bottom: 6px;">{overall}</div>
    <div style="font-size: 12px; color: #5A6C7D;">{sublabel}</div>
</div>
""", unsafe_allow_html=True)

    with c3:
        q = st.session_state.get("queries_this_session", 0)
        st.markdown(f"""
<div class="metric-card" style="border-left-color: #3B82F6;">
    <div class="eval-label">Session Activity</div>
    <div style="font-size: 34px; font-weight: 700; color: #0B1F3A;
         line-height: 1; margin-bottom: 6px;">{q}</div>
    <div style="font-size: 12px; color: #5A6C7D;">Queries this session</div>
</div>
""", unsafe_allow_html=True)

    # Module Overview
    st.markdown('<div class="section-label" style="margin-top: 28px;">Module Overview</div>',
                unsafe_allow_html=True)
    ov1, ov2 = st.columns(2)
    with ov1:
        st.markdown("""
<div class="card-gold">
    <div style="font-size: 11px; font-weight: 700; color: #8A9BB0;
         text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;">
        Knowledge Base
    </div>
    <div style="font-size: 14px; color: #2C3E50; line-height: 1.6;">
        Hybrid RAG (BM25 + ChromaDB) over SBI Mutual Fund factsheets.
        Source-cited factual answers in under 3 seconds.
    </div>
</div>
""", unsafe_allow_html=True)
        st.markdown("""
<div class="card-blue">
    <div style="font-size: 11px; font-weight: 700; color: #8A9BB0;
         text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;">
        Voice Scheduler
    </div>
    <div style="font-size: 14px; color: #2C3E50; line-height: 1.6;">
        FSM-driven voice agent for booking advisor Q&amp;A sessions with
        browser TTS and structured booking confirmation.
    </div>
</div>
""", unsafe_allow_html=True)
    with ov2:
        st.markdown("""
<div class="card-navy">
    <div style="font-size: 11px; font-weight: 700; color: #8A9BB0;
         text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;">
        Weekly Pulse
    </div>
    <div style="font-size: 14px; color: #2C3E50; line-height: 1.6;">
        LLM-generated weekly market intelligence digest with portfolio
        themes, trend analysis, and advisor action items.
    </div>
</div>
""", unsafe_allow_html=True)
        st.markdown("""
<div class="card-green">
    <div style="font-size: 11px; font-weight: 700; color: #8A9BB0;
         text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;">
        Action Approval (HITL)
    </div>
    <div style="font-size: 14px; color: #2C3E50; line-height: 1.6;">
        Human-in-the-loop review queue for Calendar, Email, and Doc
        operations before they execute on Google services.
    </div>
</div>
""", unsafe_allow_html=True)


# ── Content Routing ───────────────────────────────────────────────────────────
if page != "Home":
    st.markdown("""
<div class="brand-header">
    <span class="brand-title">INDmoney &nbsp;·&nbsp; Investor Ops &amp; Intelligence Suite</span>
    <span class="brand-sub">Investor Ops Suite</span>
</div>
""", unsafe_allow_html=True)

if page == "Home":
    render_home()
elif page == "Knowledge Base":
    from ui.tabs.tab_a import render_tab_a
    render_tab_a()
elif page == "Weekly Pulse":
    from ui.tabs.tab_b import render_tab_b
    render_tab_b()
elif page == "Voice Scheduler":
    from ui.tabs.tab_c import render_tab_c
    render_tab_c()
elif page == "Action Approval":
    from ui.tabs.tab_d import render_tab_d
    render_tab_d()
elif page == "Evaluation":
    from ui.tabs.tab_e import render_tab_e
    render_tab_e()
