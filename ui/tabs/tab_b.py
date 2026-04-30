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


def render_tab_b():
    st.header("📊 Weekly Product Pulse")
    st.caption("Analyzes INDmoney Play Store reviews to surface themes and trends.")

    reviews_path = Path("data/reviews/reviews.csv")

    pulse_file = Path("data/pulse_latest.txt")
    if pulse_file.exists():
        import datetime
        mtime = datetime.datetime.fromtimestamp(pulse_file.stat().st_mtime)
        st.caption(f"Last auto-refresh: {mtime.strftime('%Y-%m-%d %H:%M IST')} | Next: Every Monday 3:30 AM IST")
    else:
        st.caption("Auto-refresh: Every Monday 3:30 AM IST via GitHub Actions")

    if st.button("🔄 Generate Pulse", key="gen_pulse"):
        import hashlib

        reviews_hash = hashlib.md5(reviews_path.read_bytes()).hexdigest()

        with st.spinner("⏳ Generating pulse (first run ~2 min, cached after)..."):
            pulse, themes_with_trends = generate_cached_pulse(reviews_hash)

        st.session_state["pulse"] = pulse
        st.session_state["themes"] = themes_with_trends

        if themes_with_trends:
            top_theme = themes_with_trends[0].get("theme", "general")
            st.session_state["voice_top_theme"] = top_theme
            st.session_state.pop("voice_agent", None)
            st.session_state.pop("voice_history", None)
            st.success(f"✅ Pulse generated! Top theme: **{top_theme}**")
            st.info("💡 Switch to **Voice Scheduler** tab to use theme-aware booking.")
        else:
            st.success("✅ Pulse generated!")
        st.rerun()

    if "pulse" in st.session_state:
        pulse = st.session_state["pulse"]

        if pulse.get("error"):
            st.error(pulse["message"])
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Reviews Analyzed", pulse.get("total_reviews", 0))
            col2.metric("Word Count", pulse.get("word_count", 0))
            col3.metric("Date Range", f"{pulse.get('date_range', ['',''])[0]} → {pulse.get('date_range', ['',''])[1]}")

            st.markdown("### Top Themes")
            for t in st.session_state.get("themes", [])[:5]:
                trend_arrow = "🔼" if t.get("trend", {}).get("direction") == "up" else "🔽" if t.get("trend", {}).get("direction") == "down" else "➡️"
                pct = t.get("trend", {}).get("pct_delta", 0)
                st.markdown(f'<div class="metric-card">{trend_arrow} <strong>{t["theme"]}</strong> — {t["count"]} mentions ({pct:+.0f}% WoW)<br><em>"{t.get("quote", "")[:100]}"</em></div>', unsafe_allow_html=True)

            st.markdown("### Weekly Note")
            st.markdown(pulse.get("summary", ""))

            st.markdown("### Action Items")
            for i, action in enumerate(pulse.get("actions", []), 1):
                st.markdown(f"**{i}.** {action}")
