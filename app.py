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
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.01em;
}
.brand-sub {
    color: #5B7CFA;
    font-size: 13px;
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
    color: rgba(255,255,255,0.75) !important;
    font-size: 14px !important;
    padding: 8px 4px !important;
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
h1 { color: #0B1F3A; font-weight: 700; font-size: 26px; line-height: 1.25;
     margin-bottom: 6px; letter-spacing: -0.02em; }
h2 { color: #0B1F3A; font-weight: 600; font-size: 20px; line-height: 1.35;
     letter-spacing: -0.01em; }
h3 { color: #0B1F3A; font-weight: 600; font-size: 17px; line-height: 1.4; }
p, li { color: #2C3E50; font-size: 15px; line-height: 1.65; }

/* ── Cards ────────────────────────────────────────────────────────────────── */
.card {
    background: #FFFFFF; border-radius: 8px; padding: 24px;
    border: 1px solid #E8EDF3; box-shadow: 0 1px 3px rgba(11,31,58,0.06);
    margin-bottom: 16px; transition: box-shadow 0.2s ease;
}
.card:hover { box-shadow: 0 4px 12px rgba(11,31,58,0.1); }
.card-gold {
    background: #FFFFFF; border-radius: 8px; padding: 24px;
    border: 1px solid #E8EDF3; border-left: 4px solid #5B7CFA;
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
    border: 1px solid #E8EDF3; border-left: 4px solid #5B7CFA;
    box-shadow: 0 1px 3px rgba(11,31,58,0.06); margin-bottom: 12px;
    transition: box-shadow 0.2s ease;
}
.metric-card:hover { box-shadow: 0 4px 12px rgba(11,31,58,0.1); }

.answer-bullet {
    background: #FFFFFF; border-radius: 8px; padding: 16px 20px;
    border: 1px solid #E8EDF3; border-left: 4px solid #5B7CFA;
    box-shadow: 0 1px 2px rgba(11,31,58,0.04); margin-bottom: 10px;
    transition: box-shadow 0.2s ease;
}
.answer-bullet:hover { box-shadow: 0 4px 10px rgba(11,31,58,0.08); }

.hitl-op-card {
    background: #FFFFFF; border-radius: 8px; padding: 24px;
    border: 1px solid #E8EDF3; border-left: 4px solid #5B7CFA;
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
    border-color: #5B7CFA; color: #0B1F3A;
    box-shadow: 0 0 0 2px rgba(91,124,250,0.15);
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
    font-size: 12px; font-weight: 700; letter-spacing: 0.07em;
    text-transform: uppercase; color: #6B7A8D;
    margin: 0 0 18px 0; padding-bottom: 10px;
    border-bottom: 1px solid #E8EDF3;
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
    background-color: #0B1F3A !important; color: #FFFFFF !important; border: 1px solid #0B1F3A !important;
}
.stButton > button[kind="primary"] * { color: #FFFFFF !important; }
.stButton > button[kind="primary"]:hover {
    background-color: #162D4F !important; border-color: #5B7CFA !important;
    box-shadow: 0 4px 12px rgba(11,31,58,0.2);
}
.stButton > button[kind="primary"]:active { transform: scale(0.98); }
.stButton > button:not([kind="primary"]) {
    background-color: #FFFFFF; color: #0B1F3A; border: 1px solid #5B7CFA;
}
.stButton > button:not([kind="primary"]):hover {
    background-color: #FFF8EC; box-shadow: 0 2px 8px rgba(91,124,250,0.2);
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
    border-color: #5B7CFA; box-shadow: 0 0 0 3px rgba(91,124,250,0.15);
}
.stSelectbox > div > div { border: 1.5px solid #E8EDF3; border-radius: 6px; }

.stAlert { border-radius: 6px; font-size: 13px; }
hr { border: none; border-top: 1px solid #E8EDF3; margin: 24px 0; }

/* Thin scrollbars */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #F6F8FB; }
::-webkit-scrollbar-thumb { background: #D1D9E0; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #B0BEC5; }

/* ── Page transition fade-in ──────────────────────────────────────────── */
.main .block-container {
    animation: pageIn 0.18s ease-out;
}
@keyframes pageIn {
    from { opacity: 0; transform: translateY(5px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Sidebar text legibility ──────────────────────────────────────────── */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div { color: rgba(255,255,255,0.88) !important; }
</style>
""", unsafe_allow_html=True)

# ── Landing Page ──────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display: none !important; }
    .stApp {
        background: #071628 !important;
        background-image:
            radial-gradient(ellipse 80% 50% at 50% -10%, rgba(212,164,55,0.07) 0%, transparent 70%),
            radial-gradient(ellipse 60% 40% at 80% 80%, rgba(11,31,58,0.6) 0%, transparent 60%) !important;
    }
    .main .block-container {
        max-width: 1100px !important;
        padding-top: 0 !important;
        padding-left: 24px !important;
        padding-right: 24px !important;
    }
    /* Inputs */
    .stTextInput > div > div > input {
        height: 42px !important; font-size: 13px !important;
        color: #000000 !important;
        background: #FFFFFF !important;
        border: 1px solid rgba(255,255,255,0.25) !important;
        border-radius: 6px !important;
        caret-color: #5B7CFA !important;
        transition: border-color 0.15s, box-shadow 0.15s !important;
    }
    .stTextInput > div > div > input::placeholder { color: #9CA3AF !important; }
    .stTextInput > div > div > input:focus {
        border-color: #5B7CFA !important;
        box-shadow: 0 0 0 2px rgba(91,124,250,0.18) !important;
        outline: none !important;
    }
    .stTextInput label, .stTextInput label p { color: rgba(255,255,255,0.60) !important; font-size: 11px !important; letter-spacing: 0.06em !important; text-transform: uppercase !important; }
    .stTextInput { margin-bottom: 10px !important; }
    /* Glass card */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(12px) !important;
    }
    /* CTA button */
    [data-testid="stForm"] .stButton > button,
    [data-testid="stFormSubmitButton"] > button {
        background: #5B7CFA !important; border-color: #5B7CFA !important;
        color: #0B1F3A !important; font-weight: 700 !important;
        height: 42px !important; font-size: 13px !important;
        border-radius: 6px !important; letter-spacing: 0.04em !important;
        transition: background 0.15s, box-shadow 0.15s !important;
    }
    [data-testid="stForm"] .stButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        background: #4A6BE8 !important; border-color: #4A6BE8 !important;
        box-shadow: 0 4px 16px rgba(91,124,250,0.35) !important;
    }
    /* Error message */
    .stAlert { background: rgba(239,68,68,0.12) !important; border-color: rgba(239,68,68,0.3) !important; color: #FCA5A5 !important; border-radius: 6px !important; }
    </style>
    """, unsafe_allow_html=True)

    # ── Top bar ───────────────────────────────────────────────────────────────
    # ── Two-column layout: left hero + right login ────────────────────────────
    col_hero, col_form = st.columns([6, 4], gap="large")

    with col_hero:
        st.markdown("""
<div style="padding-top:20px;">
  <div style="font-size:10px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase;
       color:#5B7CFA; margin-bottom:14px;">AI-Powered Operations Platform</div>
  <div style="font-size:36px; font-weight:700; color:#FFFFFF; line-height:1.15;
       letter-spacing:-0.02em; margin-bottom:16px;">
    Investor Ops &<br>Intelligence Suite
  </div>
  <div style="font-size:14px; color:rgba(255,255,255,0.55); line-height:1.75; margin-bottom:32px; max-width:400px;">
    Enterprise-grade AI command center for fintech operations teams.
    Real-time intelligence, automated workflows, and human-in-the-loop oversight.
  </div>

  <style>
  .fc {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
    padding: 18px 20px;
    transition: background 0.18s, border-color 0.18s, transform 0.18s;
    cursor: default;
  }
  .fc:hover {
    background: rgba(91,124,250,0.09);
    border-color: rgba(91,124,250,0.35);
    transform: translateY(-2px);
  }
  .fc-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: rgba(255,255,255,0.38);
    margin-bottom: 8px;
  }
  .fc-title {
    font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.88);
    line-height: 1.35; margin-bottom: 5px;
  }
  .fc-desc {
    font-size: 11px; color: rgba(255,255,255,0.38); line-height: 1.5;
  }
  </style>
  <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; max-width:440px;">
    <div class="fc">
      <div class="fc-label">Knowledge Base</div>
      <div class="fc-title">Hybrid RAG Engine</div>
      <div class="fc-desc">BM25 + Vector · Source-cited answers</div>
    </div>
    <div class="fc">
      <div class="fc-label">Weekly Pulse</div>
      <div class="fc-title">AI Sentiment Intelligence</div>
      <div class="fc-desc">Theme extraction · Trend analysis</div>
    </div>
    <div class="fc">
      <div class="fc-label">Voice Scheduler</div>
      <div class="fc-title">FSM Voice Agent</div>
      <div class="fc-desc">Browser TTS · Booking confirmation</div>
    </div>
    <div class="fc">
      <div class="fc-label">HITL Approval</div>
      <div class="fc-title">Human-in-the-Loop Queue</div>
      <div class="fc-desc">Calendar · Email · Doc operations</div>
    </div>
    <div class="fc" style="grid-column:span 2;">
      <div class="fc-label">Evaluation</div>
      <div class="fc-title">RAG · Safety · End-to-End Evals</div>
      <div class="fc-desc">Automated quality gates · Pass/fail reporting · Compliance checks</div>
    </div>
  </div>

</div>
""", unsafe_allow_html=True)

    with col_form:
        st.markdown("""
<div style="padding-top:20px;">
  <div style="font-size:10px; font-weight:700; letter-spacing:0.10em; text-transform:uppercase;
       color:rgba(255,255,255,0.4); margin-bottom:6px;">Secure Access</div>
  <div style="font-size:20px; font-weight:700; color:#FFFFFF; margin-bottom:4px;">Sign in to your workspace</div>
  <div style="font-size:13px; color:rgba(255,255,255,0.4); margin-bottom:24px;">
    INDmoney internal operations portal
  </div>
</div>
""", unsafe_allow_html=True)

        with st.container(border=True):
            with st.form("login_form"):
                name_input  = st.text_input("Username", placeholder="Enter your name")
                email_input = st.text_input("Email",    placeholder="you@indmoney.com")
                submitted   = st.form_submit_button("Access Dashboard →",
                                                    use_container_width=True,
                                                    type="primary")
                if submitted:
                    if name_input.strip() and email_input.strip():
                        st.session_state.authenticated = True
                        st.session_state.username = name_input.strip()
                        st.session_state.email    = email_input.strip()
                        st.rerun()
                    else:
                        st.error("Please enter both username and email.")

        st.markdown("""
<div style="margin-top:12px; text-align:center; font-size:11px; color:rgba(255,255,255,0.22);">
  INDmoney Capstone 2026 &nbsp;·&nbsp; Authorized Access Only
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
         border-bottom: 1px solid #5B7CFA; margin-bottom: 16px;">
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

    # ── Data ─────────────────────────────────────────────────────────────────
    try:
        from pillars.pillar_c_hitl.approval import get_pending_ops
        pending_count = len(get_pending_ops())
    except Exception:
        pending_count = 0

    rag_path    = Path("evals/rag_eval_results.json")
    safety_path = Path("evals/safety_eval_results.json")
    if rag_path.exists() and safety_path.exists():
        try:
            rag_data   = json.loads(rag_path.read_text())
            safety_data = json.loads(safety_path.read_text())
            rag_pct    = (sum(1 for r in rag_data if r["status"] == "pass") / len(rag_data) * 100) if rag_data else 0
            safety_ok  = all(r["status"] == "pass" for r in safety_data)
            eval_label = "PASS" if rag_pct >= 70 and safety_ok else "REVIEW"
            eval_color = "#10B981" if eval_label == "PASS" else "#F59E0B"
            eval_sub   = f"RAG {rag_pct:.0f}% · Safety {'✓' if safety_ok else '✗'}"
        except Exception:
            eval_label, eval_color, eval_sub = "ERROR", "#EF4444", "Parse failed"
    else:
        eval_label, eval_color, eval_sub = "NOT RUN", "#9CA3AF", "Run evals first"

    q           = st.session_state.get("queries_this_session", 0)
    now_str     = datetime.now().strftime("%A, %d %b %Y · %H:%M")
    appr_color  = "#F59E0B" if pending_count > 0 else "#10B981"
    appr_label  = f"{pending_count} pending" if pending_count > 0 else "All clear"

    st.markdown(f"""
<style>
.hm-card {{
    background:#FFFFFF; border:1px solid #E8EDF3; border-radius:10px;
    padding:18px 20px; transition:box-shadow 0.18s, transform 0.18s;
}}
.hm-card:hover {{ box-shadow:0 6px 20px rgba(11,31,58,0.10); transform:translateY(-1px); }}
.hm-label {{
    font-size:11px; font-weight:700; letter-spacing:0.08em;
    text-transform:uppercase; color:#9CA3AF; margin-bottom:8px;
}}
.hm-val {{
    font-size:28px; font-weight:700; color:#0B1F3A;
    line-height:1; letter-spacing:-0.02em; margin-bottom:4px;
    font-variant-numeric:tabular-nums;
}}
.hm-sub {{ font-size:12px; color:#6B7280; }}
.hm-dot {{
    display:inline-block; width:7px; height:7px; border-radius:50%;
    margin-right:5px; vertical-align:middle;
}}
.mod-card {{
    background:#FFFFFF; border:1px solid #E8EDF3; border-radius:10px;
    padding:20px 22px; border-left:3px solid #5B7CFA;
    transition:box-shadow 0.18s, transform 0.18s; height:100%;
}}
.mod-card:hover {{ box-shadow:0 6px 20px rgba(11,31,58,0.10); transform:translateY(-1px); }}
.mod-name  {{ font-size:13px; font-weight:700; color:#0B1F3A; margin-bottom:4px; }}
.mod-desc  {{ font-size:12px; color:#6B7280; line-height:1.55; margin-bottom:12px; }}
.mod-stat  {{
    font-size:11px; font-weight:600; color:#5B7CFA;
    background:#EEF2FF; padding:3px 9px; border-radius:4px;
    display:inline-block; margin-right:4px; margin-top:2px;
}}
.mod-stat-green  {{
    font-size:11px; font-weight:600; color:#065F46;
    background:#D1FAE5; padding:3px 9px; border-radius:4px;
    display:inline-block; margin-right:4px; margin-top:2px;
}}
.mod-stat-amber  {{
    font-size:11px; font-weight:600; color:#92400E;
    background:#FEF3C7; padding:3px 9px; border-radius:4px;
    display:inline-block; margin-right:4px; margin-top:2px;
}}
.alert-row {{
    display:flex; align-items:flex-start; gap:12px;
    padding:12px 0; border-bottom:1px solid #F3F4F6;
}}
.alert-row:last-child {{ border-bottom:none; padding-bottom:0; }}
.alert-icon {{
    width:30px; height:30px; border-radius:7px; flex-shrink:0;
    display:flex; align-items:center; justify-content:center; font-size:13px;
}}
.alert-title {{ font-size:13px; font-weight:600; color:#1B2430; margin-bottom:2px; }}
.alert-meta  {{ font-size:11px; color:#9CA3AF; }}
</style>

<!-- date strip -->
<div style="font-size:12px; color:#9CA3AF; margin-bottom:20px; font-weight:500;">
  {now_str}
</div>
""", unsafe_allow_html=True)

    # ── Executive Metrics Strip ───────────────────────────────────────────────
    st.markdown('<div class="section-label">Operational Overview</div>', unsafe_allow_html=True)
    m1, m2, m3, m4, m5 = st.columns(5)

    metrics = [
        (m1, "System Health",  "Nominal",      "#10B981", "All 5 modules online"),
        (m2, "HITL Approvals", str(pending_count), appr_color, appr_label),
        (m3, "AI Accuracy",    eval_label,     eval_color, eval_sub),
        (m4, "Session Queries", str(q),        "#5B7CFA",  "Knowledge Base"),
        (m5, "Active Alerts",  "0",            "#10B981",  "No critical issues"),
    ]
    for col, label, val, color, sub in metrics:
        with col:
            st.markdown(f"""
<div class="hm-card" style="border-top:3px solid {color};">
  <div class="hm-label">{label}</div>
  <div class="hm-val" style="font-size:22px; color:{color};">{val}</div>
  <div class="hm-sub">{sub}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Intelligence Summary + Priority Alerts ────────────────────────────────
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown('<div class="section-label">Operational Intelligence Summary</div>', unsafe_allow_html=True)
        st.markdown(f"""
<div class="hm-card" style="border-left:3px solid #0B1F3A; padding:22px 24px;">
  <div style="font-size:11px; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;
       color:#5B7CFA; margin-bottom:10px;">AI-Generated · {datetime.now().strftime("%d %b %Y")}</div>
  <div style="font-size:15px; font-weight:700; color:#0B1F3A; margin-bottom:10px;">
    Platform operating within normal parameters.
  </div>
  <div style="font-size:13px; color:#4B5563; line-height:1.75; margin-bottom:16px;">
    Knowledge Base is live with 41 indexed chunks across 5 SBI Mutual Fund factsheets.
    Weekly Pulse has analysed <strong>300 user reviews</strong> — negative sentiment improving
    week-over-week (89.5% → 62.3%). HITL queue has
    <strong>{pending_count} pending approval{'s' if pending_count != 1 else ''}</strong>.
    Evaluation suite status: <strong style="color:{eval_color};">{eval_label}</strong>.
  </div>
  <div style="display:flex; gap:8px; flex-wrap:wrap;">
    <span style="font-size:11px; font-weight:600; color:#065F46; background:#D1FAE5;
          padding:3px 10px; border-radius:4px;">KB Online</span>
    <span style="font-size:11px; font-weight:600; color:#1D4ED8; background:#DBEAFE;
          padding:3px 10px; border-radius:4px;">Pulse Active</span>
    <span style="font-size:11px; font-weight:600; color:#5B21B6; background:#EDE9FE;
          padding:3px 10px; border-radius:4px;">Voice Ready</span>
    <span style="font-size:11px; font-weight:600; color:{("#065F46" if eval_label=="PASS" else "#92400E")};
          background:{("#D1FAE5" if eval_label=="PASS" else "#FEF3C7")};
          padding:3px 10px; border-radius:4px;">Evals {eval_label}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-label">Priority Alerts</div>', unsafe_allow_html=True)
        alerts = []
        if pending_count > 0:
            alerts.append(("⚠", "#FEF3C7", "#92400E", f"{pending_count} HITL operation(s) awaiting approval", "Action Approval · Immediate"))
        if eval_label not in ("PASS", "NOT RUN"):
            alerts.append(("✗", "#FEE2E2", "#991B1B", "Evaluation suite needs attention", f"Evaluation · {eval_sub}"))
        if not alerts:
            alerts.append(("✓", "#D1FAE5", "#065F46", "No active alerts", "All systems nominal"))
        alerts += [
            ("◎", "#EEF2FF", "#3730A3", "Weekly Pulse: UI regression still top theme", "Weekly Pulse · High severity"),
            ("◎", "#EEF2FF", "#3730A3", "Order failure rate elevated this week", "Weekly Pulse · Monitor"),
        ]
        st.markdown('<div class="hm-card" style="padding:18px 20px;">', unsafe_allow_html=True)
        for icon, bg, color, title, meta in alerts[:4]:
            st.markdown(f"""
<div class="alert-row">
  <div class="alert-icon" style="background:{bg}; color:{color};">{icon}</div>
  <div>
    <div class="alert-title">{title}</div>
    <div class="alert-meta">{meta}</div>
  </div>
</div>
""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Module Cards ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Platform Modules</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c4, c5     = st.columns(2)

    modules = [
        (c1, "Knowledge Base",     "Hybrid RAG over SBI Mutual Fund factsheets. Source-cited answers with BM25 + vector retrieval.",
         [("41 chunks", "mod-stat"), ("5 funds", "mod-stat"), ("BM25 + Vector", "mod-stat-green")]),
        (c2, "Weekly Pulse",       "AI sentiment intelligence from 300 Play Store reviews. Theme extraction and trend analysis.",
         [("300 reviews", "mod-stat"), ("62.3% neg", "mod-stat-amber"), ("↓ Improving", "mod-stat-green")]),
        (c3, "Voice Scheduler",    "FSM-driven voice agent for booking advisor sessions with browser TTS.",
         [("FSM Agent", "mod-stat"), ("TTS Ready", "mod-stat-green"), ("Booking Flow", "mod-stat")]),
        (c4, "Action Approval",    "Human-in-the-loop review queue for Calendar, Email, and Doc operations before execution.",
         [("%d pending" % pending_count, "mod-stat-amber" if pending_count > 0 else "mod-stat-green"), ("HITL Queue", "mod-stat"), ("Google APIs", "mod-stat")]),
        (c5, "Evaluation",         "Automated quality gates covering RAG accuracy, safety checks, and end-to-end pipeline validation.",
         [(eval_label, "mod-stat-green" if eval_label == "PASS" else "mod-stat-amber"), (eval_sub.split("·")[0].strip(), "mod-stat"), ("Safety Checks", "mod-stat")]),
    ]

    for col, name, desc, stats in modules:
        with col:
            stats_html = " ".join(f'<span class="{cls}">{lbl}</span>' for lbl, cls in stats)
            st.markdown(f"""
<div class="mod-card">
  <div class="mod-name">{name}</div>
  <div class="mod-desc">{desc}</div>
  <div>{stats_html}</div>
</div>
""", unsafe_allow_html=True)


# ── Persistent brand header — always shown on every page ─────────────────────
_welcome = (
    f"Welcome back, {st.session_state.username}"
    if page == "Home"
    else page
)
st.markdown(f"""
<div class="brand-header">
    <span class="brand-title">INDmoney &nbsp;·&nbsp; Investor Ops &amp; Intelligence Suite</span>
    <span class="brand-sub">{_welcome}</span>
</div>
""", unsafe_allow_html=True)

# ── Content Routing ───────────────────────────────────────────────────────────
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
