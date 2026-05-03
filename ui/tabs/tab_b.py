import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@st.cache_data(ttl=3600, show_spinner=False)
def generate_cached_pulse(reviews_hash: str):
    """Generate pulse with 1-hour cache. reviews_hash busts cache when CSV changes."""
    import pandas as pd
    from pillars.pillar_b_voice.themes import extract_themes
    from pillars.pillar_b_voice.trends import compute_trends
    from pillars.pillar_b_voice.pulse import generate_pulse

    reviews_path = Path("data/reviews/reviews.csv")
    df = pd.read_csv(reviews_path)
    total = len(df)
    dates = pd.to_datetime(df["review_date"])
    date_range = (dates.min().strftime("%Y-%m-%d"), dates.max().strftime("%Y-%m-%d"))

    themes = extract_themes(reviews_path)
    themes_with_trends = compute_trends(themes, reviews_path)
    pulse = generate_pulse(themes_with_trends, total, date_range)

    return pulse, themes_with_trends


@st.fragment
def _display_pulse_results() -> None:
    """Render pulse stats, themes, and action items. Isolated so Generate button
    doesn't re-render the whole page — only this section updates."""
    pulse = st.session_state["pulse"]

    if pulse.get("error"):
        st.error(pulse["message"])
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Reviews Analyzed", pulse.get("total_reviews", 0))
    col2.metric("Word Count", pulse.get("word_count", 0))
    col3.metric(
        "Date Range",
        f"{pulse.get('date_range', ['',''])[0]}",
        f"→ {pulse.get('date_range', ['',''])[1]}",
    )

    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.markdown('<div class="section-label">Top Themes</div>', unsafe_allow_html=True)
        for t in st.session_state.get("themes", [])[:5]:
            direction = t.get("trend", {}).get("direction")
            trend_label = "UP" if direction == "up" else "DOWN" if direction == "down" else "FLAT"
            trend_color = "#10B981" if direction == "up" else "#EF4444" if direction == "down" else "#5A6C7D"
            pct = t.get("trend", {}).get("pct_delta", 0)
            st.markdown(f"""
<div class="metric-card">
    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <strong style="color: #0B1F3A; font-size: 14px;">{t["theme"]}</strong>
        <span style="font-size: 11px; font-weight: 700; color: {trend_color};
              letter-spacing: 0.05em; background: {'#D1FAE5' if direction == 'up' else '#FEE2E2' if direction == 'down' else '#F3F4F6'};
              padding: 2px 8px; border-radius: 10px;">
            {trend_label}&nbsp;{pct:+.0f}%
        </span>
    </div>
    <div style="color: #8A9BB0; font-size: 12px; margin-top: 4px;">{t["count"]} mentions this week</div>
    <div style="color: #5A6C7D; font-size: 13px; margin-top: 10px; font-style: italic; line-height: 1.5;">
        &ldquo;{t.get("quote", "")[:100]}&rdquo;
    </div>
</div>
""", unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="section-label">Weekly Note</div>', unsafe_allow_html=True)
        st.markdown(f"""
<div class="card-navy">
    <div style="color: #2C3E50; font-size: 14px; line-height: 1.7;">{pulse.get("summary", "")}</div>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="section-label" style="margin-top: 24px;">Action Items</div>',
                    unsafe_allow_html=True)
        for i, action in enumerate(pulse.get("actions", []), 1):
            st.markdown(f"""
<div style="display: flex; gap: 12px; align-items: flex-start;
     padding: 10px 0; border-bottom: 1px solid #F0F3F6;">
    <span style="background: #0B1F3A; color: #D4A437; min-width: 22px; height: 22px;
          border-radius: 50%; display: inline-flex; align-items: center;
          justify-content: center; font-size: 11px; font-weight: 700;
          flex-shrink: 0; margin-top: 1px;">{i}</span>
    <span style="color: #2C3E50; font-size: 13px; line-height: 1.55;">{action}</span>
</div>
""", unsafe_allow_html=True)


def render_tab_b():
    if "tab_b_initialized" not in st.session_state:
        st.session_state["tab_b_initialized"] = True

    st.header("Weekly Product Pulse")
    st.caption("Analyzes INDmoney Play Store reviews to surface themes and trends.")

    reviews_path = Path("data/reviews/reviews.csv")

    # Schedule info bar
    pulse_file = Path("data/pulse_latest.txt")
    if pulse_file.exists():
        import datetime
        mtime = datetime.datetime.fromtimestamp(pulse_file.stat().st_mtime)
        schedule_text = f"Last refresh: {mtime.strftime('%Y-%m-%d %H:%M IST')}&nbsp;&nbsp;|&nbsp;&nbsp;Next: Monday 03:30 IST"
    else:
        schedule_text = "Auto-refresh: Every Monday 03:30 IST via GitHub Actions"

    st.markdown(f"""
<div style="display: flex; align-items: center; justify-content: space-between;
     padding: 10px 16px; background: #FFFFFF; border-radius: 6px;
     border: 1px solid #E8EDF3; margin-bottom: 20px; font-size: 12px; color: #8A9BB0;">
    <span>{schedule_text}</span>
</div>
""", unsafe_allow_html=True)

    if st.button("Generate Pulse", key="gen_pulse", type="primary"):
        import hashlib
        reviews_hash = hashlib.md5(reviews_path.read_bytes()).hexdigest()

        with st.spinner("Generating pulse (first run ~2 min, cached after)…"):
            pulse, themes_with_trends = generate_cached_pulse(reviews_hash)

        st.session_state["pulse"] = pulse
        st.session_state["themes"] = themes_with_trends

        if themes_with_trends:
            top_theme = themes_with_trends[0].get("theme", "general")
            st.session_state["voice_top_theme"] = top_theme
            st.session_state.pop("voice_agent", None)
            st.session_state.pop("voice_history", None)
            st.success(f"Pulse generated. Top theme: **{top_theme}**")
            st.info("Switch to **Voice Scheduler** to use theme-aware booking.")
        else:
            st.success("Pulse generated.")
        st.rerun()

    if "pulse" not in st.session_state:
        st.markdown("""
<div class="empty-state" style="margin-top: 32px;">
    <div class="empty-state-icon">📊</div>
    <h3>No pulse data yet</h3>
    <p>Click <strong>Generate Pulse</strong> above to analyze the latest reviews.</p>
</div>
""", unsafe_allow_html=True)
        return

    _display_pulse_results()
