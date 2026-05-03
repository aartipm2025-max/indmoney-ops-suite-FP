import streamlit as st
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

_FUNDS = [
    "SBI Bluechip Fund",
    "SBI Small Cap Fund",
    "SBI Midcap Fund",
    "SBI Equity Hybrid Fund",
    "SBI ELSS Tax Saver",
]

_EXAMPLES = [
    "What is the exit load for SBI Bluechip Fund?",
    "What is exit load and how is it calculated?",
    "What is the minimum SIP for ELSS fund?",
]

_ROUTE_BADGE = {
    "fact_only": ("route-fact_only", "Fact"),
    "fee_only":  ("route-fee_only",  "Fee"),
    "both":      ("route-both",       "Fact + Fee"),
}


@st.fragment
def _display_answer(result: dict) -> None:
    """Render answer bullets + sources. Isolated so only this re-renders on result change."""
    if result.get("refused"):
        st.warning(result["message"])
        if result.get("educational_link"):
            st.markdown(f"[Learn more]({result['educational_link']})")
        return

    if result.get("error"):
        st.error(result["message"])
        return

    route_key = result.get("route", "")
    badge_cls, badge_label = _ROUTE_BADGE.get(route_key, ("route-default", route_key or "N/A"))
    model_name = result.get("model_name", "N/A")

    st.markdown(f"""
<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px;">
    <span class="route-badge {badge_cls}">{badge_label}</span>
    <span style="font-size: 12px; color: #8A9BB0;">via {model_name}</span>
</div>
""", unsafe_allow_html=True)

    st.markdown("### Answer")

    all_sources = set()
    for i, bullet in enumerate(result.get("bullets", []), 1):
        text = bullet.get("text", "")
        sources = re.findall(r'\[source:([^\]]+)\]', text)
        all_sources.update(sources)
        clean_text = re.sub(r'\s*\[source:[^\]]+\]\s*', ' ', text)
        clean_text = re.sub(r'\[doc_id=[^\]]+\]', '', clean_text).strip()
        st.markdown(f"""
<div class="answer-bullet">
    <div style="font-size: 14px; line-height: 1.65; color: #2C3E50;">
        <span style="font-weight: 700; color: #0B1F3A;">{i}.</span>&nbsp; {clean_text}
    </div>
</div>
""", unsafe_allow_html=True)

    if all_sources:
        clean_sources = []
        for s in sorted(all_sources):
            clean_s = s.replace('doc_id=', '').strip()
            if clean_s not in clean_sources:
                clean_sources.append(clean_s)
        source_tags = " ".join(
            f'<span class="source-tag">{s}</span>' for s in clean_sources
        )
        st.markdown(f"""
<div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid #E8EDF3;">
    <div class="section-label" style="margin-bottom: 10px;">Sources Referenced</div>
    {source_tags}
</div>
""", unsafe_allow_html=True)


def render_tab_a():
    if "tab_a_initialized" not in st.session_state:
        st.session_state["tab_a_initialized"] = True

    st.markdown("### 💼 Knowledge Base")
    st.caption("Ask factual questions about SBI Mutual Funds")

    # ── Fund chips bar ────────────────────────────────────────────────────────
    st.markdown("**Available Funds:**")
    fund_cols = st.columns(len(_FUNDS))
    for idx, fund in enumerate(_FUNDS):
        with fund_cols[idx]:
            st.markdown(f"""
<div style="
    background: white;
    border: 1px solid #E8EDF3;
    border-left: 3px solid #D4A437;
    border-radius: 6px;
    padding: 8px 12px;
    text-align: center;
    font-size: 12px;
    color: #0B1F3A;
    font-weight: 500;
">{fund.replace('SBI ', '')}</div>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Clickable example buttons ─────────────────────────────────────────────
    st.markdown("**Try these examples:**")
    ex_cols = st.columns(len(_EXAMPLES))
    for idx, ex in enumerate(_EXAMPLES):
        with ex_cols[idx]:
            if st.button(ex, key=f"ex_{idx}", use_container_width=True):
                st.session_state.query_input = ex
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Centered search bar ───────────────────────────────────────────────────
    _, mid, _ = st.columns([1, 3, 1])
    with mid:
        query = st.text_input(
            "Ask your question",
            placeholder="e.g., What is the expense ratio of SBI Small Cap Fund?",
            key="query_input",
            label_visibility="collapsed",
        )
        search_clicked = st.button(
            "🔍 Search",
            type="primary",
            use_container_width=True,
            key="search_btn",
        )

    # ── Run search when button is clicked ─────────────────────────────────────
    if search_clicked and query:
        with st.spinner("Searching knowledge base…"):
            from pillars.pillar_a_knowledge.answerer import ask
            result = ask(query)
        st.session_state["tab_a_result"] = result
        st.session_state["tab_a_query"] = query

    # ── Display results ───────────────────────────────────────────────────────
    result = st.session_state.get("tab_a_result")
    if result:
        _display_answer(result)

    st.markdown("""
<div style="margin-top: 32px; padding: 12px 16px; background: #FFFFFF; border-radius: 6px;
     border: 1px solid #E8EDF3; font-size: 12px; color: #8A9BB0;">
    Facts only &mdash; no investment advice. Source data last updated: 2026-04-23.
</div>
""", unsafe_allow_html=True)
