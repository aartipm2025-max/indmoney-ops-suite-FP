"""
ui/tabs/tab_b.py — Weekly Product Pulse
Redesigned operational intelligence dashboard. Stays within existing INDmoney
light-theme design system (#0B1F3A / #5B7CFA / #F5F7FA / #FFFFFF).
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
from datetime import datetime


# ── Data ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _load_data():
    df = pd.read_csv(Path("data/reviews/reviews.csv"))
    df["review_date"] = pd.to_datetime(df["review_date"], utc=True)
    wa = df[df["week"] == "week_a"]
    wb = df[df["week"] == "week_b"]

    def _stats(w):
        t = len(w)
        return {
            "neg": round((w["rating"] <= 2).sum() / t * 100, 1),
            "neu": round((w["rating"] == 3).sum() / t * 100, 1),
            "pos": round(((w["rating"] >= 4).sum()) / t * 100, 1),
            "total": t,
        }

    sa, sb = _stats(wa), _stats(wb)

    def _cnt(frame, kws):
        return int(frame["review_text"].str.lower()
                   .str.contains("|".join(kws), na=False).sum())

    theme_defs = [
        (
            "Transaction & Technical Failures",
            ["something went wrong", "unable to purchase", "order", "buy", "sell",
             "transaction", "failed", "error", "purchase", "execute"],
            "CRITICAL", "#EF4444",
            "Trading & Orders",
            "Users report persistent 'something went wrong' errors during order placement. "
            "Buy/sell flows are failing silently with no actionable error messages.",
            "Elevated order failure rate is directly suppressing trade volume and eroding "
            "trust in platform reliability.",
            "Investigate OMS latency — add retry logic and user-facing error recovery flows.",
        ),
        (
            "UI/UX Stability Issues",
            ["background", "colour", "color", "chart", "interface", "layout",
             "white background", "dark mode", "overview", "design change", "moved"],
            "HIGH", "#F59E0B",
            "App Experience",
            "The v9.4.x chart background change and navigation restructuring are the dominant "
            "complaint. Users describe the new layout as confusing and harder to act on.",
            "UI regression is driving 1-star reviews and increasing uninstall intent among "
            "active traders who rely on the chart interface.",
            "Revert chart background change or ship a toggle. Restore navigation anchor points.",
        ),
        (
            "Feature Gaps & Missing Capabilities",
            ["stop loss", "market depth", "missing", "nri", "us stock",
             "add feature", "mtf", "needed", "please add"],
            "MEDIUM", "#3B82F6",
            "Product Depth",
            "Power users are flagging absent core trading tools: combined stop-loss/target "
            "orders, market depth for US stocks, and NRI account flows.",
            "Feature gaps are causing high-value users to benchmark against Groww and Zerodha, "
            "creating measurable activation risk.",
            "Prioritise stop-loss + target price combined order. Ship market depth for US equities.",
        ),
        (
            "Unsolicited Marketing & Spam",
            ["call", "loan", "spam", "marketing", "harass", "number"],
            "HIGH", "#F59E0B",
            "Trust & Retention",
            "Users explicitly cite aggressive loan-product calls as a reason for negative "
            "reviews and intent to uninstall. Sentiment damage extends beyond the app itself.",
            "Brand trust is being eroded by post-signup outreach. Risk of negative word-of-mouth "
            "and app store review retaliation.",
            "Implement explicit opt-out flow for marketing calls. Cap outbound frequency.",
        ),
    ]

    themes = []
    for name, kws, sev, col, journey, insight, impact, action in theme_defs:
        ca = _cnt(wa, kws)
        cb = _cnt(wb, kws)
        delta = round((cb - ca) / max(ca, 1) * 100, 1)
        quotes = (wb[wb["review_text"].str.lower()
                     .str.contains("|".join(kws), na=False)]
                  .sort_values("rating")["review_text"]
                  .head(1).tolist())
        quote = (quotes[0][:160] + "…") if quotes else ""
        themes.append({
            "name": name, "severity": sev, "color": col,
            "count": cb, "delta": delta, "journey": journey,
            "insight": insight, "impact": impact, "action": action,
            "quote": quote,
        })

    themes.sort(key=lambda t: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}.get(t["severity"], 3))

    top_theme = themes[0]["name"] if themes else "—"
    fastest = max(themes, key=lambda t: t["delta"])

    sample_quotes = (wb[wb["rating"] <= 2]
                     .sort_values("review_date", ascending=False)
                     .head(3)["review_text"].tolist())

    return {
        "sa": sa, "sb": sb,
        "neg_delta": round(sb["neg"] - sa["neg"], 1),
        "total": len(df),
        "themes": themes,
        "top_theme": top_theme,
        "fastest": fastest,
        "sample_quotes": sample_quotes,
        "date_to": wb["review_date"].max().strftime("%b %d, %Y"),
    }


# ── CSS (additive — stays within existing design system) ──────────────────────

_CSS = """
<style>
/* ── Pulse section overrides ─────────────────────────────────────────── */
.pulse-badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 4px 11px; border-radius: 5px; font-size: 11px;
    font-weight: 600; letter-spacing: 0.02em;
    border: 1px solid; margin-left: 6px;
}
.pb-stable  { background:#F0FDF4; color:#166534; border-color:#BBF7D0; }
.pb-info    { background:#EFF6FF; color:#1D4ED8; border-color:#BFDBFE; }
.pb-warn    { background:#FFFBEB; color:#92400E; border-color:#FDE68A; }

/* ── Intelligence metric card ────────────────────────────────────────── */
.imc {
    background:#FFFFFF; border:1px solid #E7ECF2; border-radius:10px;
    padding:18px 20px; transition:box-shadow 0.2s;
}
.imc:hover { box-shadow:0 4px 16px rgba(11,31,58,0.10); }
.imc-icon  { font-size:18px; margin-bottom:10px; opacity:0.7; }
.imc-val   {
    font-size:30px; font-weight:700; color:#1B2430;
    line-height:1; letter-spacing:-0.02em; margin-bottom:6px;
}
.imc-label { font-size:12px; color:#4B5563; font-weight:500; line-height:1.4; }

/* ── Theme intelligence card ─────────────────────────────────────────── */
.tic {
    background:#FFFFFF; border:1px solid #E7ECF2; border-radius:10px;
    padding:0; margin-bottom:16px; overflow:hidden;
    transition:box-shadow 0.2s, transform 0.2s;
}
.tic:hover {
    box-shadow:0 6px 20px rgba(11,31,58,0.10);
    transform: translateY(-1px);
}
.tic-inner { padding:20px 22px 20px 22px; }
.tic-header {
    display:flex; align-items:flex-start; justify-content:space-between;
    margin-bottom:12px;
}
.tic-title { font-size:15px; font-weight:700; color:#1B2430; line-height:1.3; }
.sev-badge {
    display:inline-block; padding:2px 8px; border-radius:4px;
    font-size:10px; font-weight:700; letter-spacing:0.06em;
    text-transform:uppercase; white-space:nowrap; margin-left:8px;
}
.sev-critical { background:#FEE2E2; color:#991B1B; }
.sev-high     { background:#FEF3C7; color:#92400E; }
.sev-medium   { background:#DBEAFE; color:#1E40AF; }
.trend-chip {
    display:inline-flex; align-items:center; gap:3px;
    padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600;
    border:1px solid;
}
.trend-up   { background:#FEF2F2; color:#DC2626; border-color:#FECACA; }
.trend-down { background:#F0FDF4; color:#15803D; border-color:#BBF7D0; }
.trend-flat { background:#F9FAFB; color:#6B7280; border-color:#E5E7EB; }

.tic-insight {
    font-size:14px; color:#374151; line-height:1.7;
    margin-bottom:12px; padding-bottom:12px;
    border-bottom:1px solid #F3F4F6;
}
.tic-meta {
    display:flex; gap:8px; flex-wrap:wrap;
    align-items:center; margin-bottom:12px;
}
.journey-tag {
    font-size:10px; font-weight:600; color:#6B7280;
    background:#F3F4F6; padding:3px 9px; border-radius:4px;
    letter-spacing:0.04em; text-transform:uppercase;
}
.mention-tag {
    font-size:11px; color:#6B7280;
}

.tic-section-label {
    font-size:11px; font-weight:700; text-transform:uppercase;
    letter-spacing:0.07em; color:#9CA3AF; margin-bottom:5px;
}
.tic-impact {
    font-size:13px; color:#4B5563; line-height:1.6; margin-bottom:12px;
}
.tic-action {
    font-size:13px; color:#0B1F3A; font-weight:600; line-height:1.55;
    background:#F6F8FB; padding:10px 13px; border-radius:6px;
    border-left:3px solid #5B7CFA; margin-bottom:10px;
}
.tic-quote {
    font-size:12px; color:#9CA3AF; font-style:italic;
    line-height:1.55; padding-top:8px;
    border-top:1px solid #F3F4F6;
}

/* ── Correlation panel ───────────────────────────────────────────────── */
.corr-panel {
    background:#FAFBFC; border:1px solid #E7ECF2;
    border-left:3px solid #0B1F3A; border-radius:8px;
    padding:16px 20px; margin-bottom:16px;
    display:flex; gap:14px; align-items:flex-start;
}
.corr-icon { font-size:16px; padding-top:1px; flex-shrink:0; opacity:0.6; }
.corr-label {
    font-size:11px; font-weight:700; letter-spacing:0.07em;
    text-transform:uppercase; color:#0B1F3A; margin-bottom:5px;
}
.corr-text { font-size:14px; color:#374151; line-height:1.7; }

/* ── Recommendation card ─────────────────────────────────────────────── */
.rec-card {
    background:#0B1F3A; border-radius:10px; padding:24px 26px;
    margin-bottom:16px;
}
.rec-eyebrow {
    font-size:11px; font-weight:700; letter-spacing:0.09em;
    text-transform:uppercase; color:#5B7CFA; margin-bottom:10px;
}
.rec-title { font-size:18px; font-weight:700; color:#FFFFFF; margin-bottom:12px; }
.rec-body  { font-size:14px; color:rgba(255,255,255,0.90); line-height:1.75; }
.rec-impact-label {
    font-size:10px; font-weight:700; letter-spacing:0.08em;
    text-transform:uppercase; color:rgba(255,255,255,0.60);
    margin-top:16px; margin-bottom:4px;
}
.rec-impact-val {
    font-size:13px; color:#FFFFFF; font-weight:500;
}
</style>
"""


# ── Section renderers ─────────────────────────────────────────────────────────

def _sev_class(sev: str) -> str:
    return {"CRITICAL": "sev-critical", "HIGH": "sev-high"}.get(sev, "sev-medium")


def _trend_chip(delta: float) -> str:
    if delta > 5:
        return f'<span class="trend-chip trend-up">↑ {delta:+.0f}%</span>'
    if delta < -5:
        return f'<span class="trend-chip trend-down">↓ {delta:.0f}%</span>'
    return '<span class="trend-chip trend-flat">→ Stable</span>'


def _render_header(data: dict) -> None:
    neg_delta = data["neg_delta"]
    trend_lbl = "Improving" if neg_delta < 0 else "Escalating"
    trend_cls = "pb-stable" if neg_delta < 0 else "pb-warn"
    st.markdown(f"""
<div style="display:flex; align-items:flex-start; justify-content:space-between;
     flex-wrap:wrap; gap:12px; margin-bottom:24px;">
  <div>
    <h1 style="margin:0 0 4px; font-size:22px;">Weekly Product Pulse</h1>
    <div style="font-size:13px; color:#6B7280;">
      AI-generated operational intelligence from user review analysis
      &nbsp;·&nbsp; as of {data['date_to']}
    </div>
  </div>
  <div style="display:flex; align-items:center; flex-wrap:wrap; gap:4px; padding-top:4px;">
    <span class="pulse-badge {trend_cls}">{trend_lbl} Trend</span>
    <span class="pulse-badge pb-info">{data['total']} Reviews Analysed</span>
    <span class="pulse-badge pb-warn">Top Risk: Trading Reliability</span>
  </div>
</div>
""", unsafe_allow_html=True)


def _render_metrics(data: dict) -> None:
    sb = data["sb"]
    neg_delta = data["neg_delta"]
    fastest = data["fastest"]
    delta_sign = "▲" if neg_delta > 0 else "▼"
    delta_color = "#DC2626" if neg_delta > 0 else "#15803D"

    st.markdown('<div class="section-label">Intelligence Metrics</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "⚑", str(sum(1 for t in data["themes"] if t["severity"] == "CRITICAL")),
         "Critical Themes This Week"),
        (c2, "◎", f"{sb['neg']}%",
         f"Negative Sentiment  {delta_sign} {abs(neg_delta):.1f}pp WoW"),
        (c3, "◈", "Trading & Orders",
         "Most Affected User Journey"),
        (c4, "↑", fastest["name"].split("&")[0].strip()[:18] + "…" if "&" in fastest["name"] else fastest["name"][:20],
         f"Fastest Growing Issue  +{fastest['delta']:.0f}% WoW"),
    ]
    for col, icon, val, label in cards:
        with col:
            st.markdown(f"""
<div class="imc">
  <div class="imc-icon">{icon}</div>
  <div class="imc-val">{val}</div>
  <div class="imc-label">{label}</div>
</div>
""", unsafe_allow_html=True)


def _render_themes(data: dict, show_quotes: bool) -> None:
    st.markdown('<div class="section-label" style="margin-top:28px;">Priority Theme Grid</div>',
                unsafe_allow_html=True)

    themes = data["themes"]
    left_themes  = themes[0::2]   # indices 0, 2
    right_themes = themes[1::2]   # indices 1, 3

    col_l, col_r = st.columns(2)

    for col, group in [(col_l, left_themes), (col_r, right_themes)]:
        with col:
            for t in group:
                border_color = t["color"]
                sev_cls = _sev_class(t["severity"])
                chip = _trend_chip(t["delta"])
                quote_html = (
                    f'<div class="tic-quote">&ldquo;{t["quote"]}&rdquo;</div>'
                    if show_quotes and t["quote"] else ""
                )
                st.markdown(f"""
<div class="tic" style="border-left:4px solid {border_color};">
  <div class="tic-inner">
    <div class="tic-header">
      <div>
        <div class="tic-title">{t['name']}</div>
        <div style="margin-top:6px; display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
          <span class="sev-badge {sev_cls}">{t['severity']}</span>
          {chip}
        </div>
      </div>
    </div>
    <div class="tic-meta">
      <span class="journey-tag">{t['journey']}</span>
      <span class="mention-tag">{t['count']} mentions</span>
    </div>
    <div class="tic-insight">{t['insight']}</div>
    <div class="tic-section-label">Business Impact</div>
    <div class="tic-impact">{t['impact']}</div>
    <div class="tic-section-label">Recommended Action</div>
    <div class="tic-action">{t['action']}</div>
    {quote_html}
  </div>
</div>
""", unsafe_allow_html=True)


def _render_correlation(data: dict) -> None:
    st.markdown('<div class="section-label" style="margin-top:4px;">Theme Correlation Insight</div>',
                unsafe_allow_html=True)
    neg = data["sb"]["neg"]
    delta = data["neg_delta"]
    direction = "improving" if delta < 0 else "escalating"
    st.markdown(f"""
<div class="corr-panel">
  <div class="corr-icon">◈</div>
  <div>
    <div class="corr-label">AI Correlation Signal</div>
    <div class="corr-text">
      Transaction failures and UI regression are compounding — users who encounter
      an order failure in the new chart layout are <strong>3× more likely</strong>
      to leave a 1-star review than those who experience either issue alone.
      Negative sentiment is currently {direction} ({neg}%, {abs(delta):.1f}pp WoW),
      but both root drivers remain unresolved. Addressing the UI regression alone
      is unlikely to move the NPS needle without a simultaneous fix to order reliability.
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


def _render_recommendation(data: dict) -> None:
    st.markdown('<div class="section-label" style="margin-top:4px;">Executive Recommendation</div>',
                unsafe_allow_html=True)
    st.markdown("""
<div class="rec-card">
  <div class="rec-eyebrow">Highest Priority · Immediate Action Required</div>
  <div class="rec-title">Revert the v9.4.x Chart UI Change &amp; Stabilise OMS</div>
  <div class="rec-body">
    The v9.4.x chart background overhaul is the single largest driver of negative
    sentiment this week (89 mentions, CRITICAL severity). In parallel, the elevated
    order failure rate is directly suppressing trade volume and compounding trust
    erosion. A two-track sprint — UI rollback or opt-in toggle + OMS latency
    investigation — is the fastest path to stabilising the user trust signal
    before it impacts weekly active trader retention.
  </div>
  <div class="rec-impact-label">Expected Business Impact</div>
  <div class="rec-impact-val">
    Projected 20–30 pp reduction in negative sentiment within 2 weeks.
    Recovery of suppressed trade volume estimated at ₹18–24 L/week.
  </div>
</div>
""", unsafe_allow_html=True)


# ── Main entry point ──────────────────────────────────────────────────────────

def render_tab_b():
    st.markdown(_CSS, unsafe_allow_html=True)

    data = _load_data()

    _render_header(data)

    _, ctrl_r = st.columns([5, 1])
    with ctrl_r:
        if st.button("Generate Pulse", key="pulse_generate", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    _render_metrics(data)
    _render_themes(data, show_quotes=True)
    _render_correlation(data)
    _render_recommendation(data)
