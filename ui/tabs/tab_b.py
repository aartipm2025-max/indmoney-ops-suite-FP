import streamlit as st
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def render_tab_b():
    st.header("📊 Weekly Pulse & Voice Agent")

    pulse_tab, voice_tab = st.tabs(["📋 Weekly Pulse", "🎙️ Voice Agent"])

    with pulse_tab:
        st.subheader("Generate Weekly Product Pulse")
        st.caption("Analyzes real INDmoney Play Store reviews to surface themes and trends.")

        reviews_path = Path("data/reviews/reviews.csv")

        pulse_file = Path("data/pulse_latest.txt")
        if pulse_file.exists():
            import datetime
            mtime = datetime.datetime.fromtimestamp(pulse_file.stat().st_mtime)
            st.caption(f"Last auto-refresh: {mtime.strftime('%Y-%m-%d %H:%M IST')} | Next: Every Monday 3:30 AM IST")
        else:
            st.caption("Auto-refresh: Every Monday 3:30 AM IST via GitHub Actions")

        if st.button("🔄 Generate Pulse", key="gen_pulse"):
            import pandas as pd
            from pillars.pillar_b_voice.themes import extract_themes
            from pillars.pillar_b_voice.trends import compute_trends
            from pillars.pillar_b_voice.pulse import generate_pulse

            df = pd.read_csv(reviews_path)
            total = len(df)
            dates = pd.to_datetime(df["review_date"])
            date_range = (dates.min().strftime("%Y-%m-%d"), dates.max().strftime("%Y-%m-%d"))

            # Progress bar
            progress = st.progress(0)
            status = st.empty()

            status.text("Extracting themes from 300 reviews...")
            themes = extract_themes(reviews_path)
            progress.progress(50)

            status.text("Computing week-over-week trends...")
            themes_with_trends = compute_trends(themes, reviews_path)
            progress.progress(75)

            status.text("Generating weekly pulse summary...")
            pulse = generate_pulse(themes_with_trends, total, date_range)
            progress.progress(100)

            status.empty()
            progress.empty()

            st.session_state["pulse"] = pulse
            st.session_state["themes"] = themes_with_trends

            # Auto-update voice theme
            if themes_with_trends:
                st.session_state["voice_top_theme"] = themes_with_trends[0].get("theme", "general")
                st.session_state.pop("voice_agent", None)
                st.session_state.pop("voice_history", None)

            st.success("✅ Pulse generated!")
            st.rerun()

        if "pulse" in st.session_state:
            pulse = st.session_state["pulse"]

            if pulse.get("error"):
                st.error(pulse["message"])
            else:
                # Metrics row
                col1, col2, col3 = st.columns(3)
                col1.metric("Reviews Analyzed", pulse.get("total_reviews", 0))
                col2.metric("Word Count", pulse.get("word_count", 0))
                col3.metric("Date Range", f"{pulse.get('date_range', ['',''])[0]} → {pulse.get('date_range', ['',''])[1]}")

                # Themes
                st.markdown("### Top Themes")
                for t in st.session_state.get("themes", [])[:5]:
                    trend_arrow = "🔼" if t.get("trend", {}).get("direction") == "up" else "🔽" if t.get("trend", {}).get("direction") == "down" else "➡️"
                    pct = t.get("trend", {}).get("pct_delta", 0)
                    st.markdown(f'<div class="metric-card">{trend_arrow} <strong>{t["theme"]}</strong> — {t["count"]} mentions ({pct:+.0f}% WoW)<br><em>"{t.get("quote", "")[:100]}"</em></div>', unsafe_allow_html=True)

                # Pulse summary
                st.markdown("### Weekly Note")
                st.markdown(pulse.get("summary", ""))

                # Actions
                st.markdown("### Action Items")
                for i, action in enumerate(pulse.get("actions", []), 1):
                    st.markdown(f"**{i}.** {action}")

    with voice_tab:
        st.subheader("🎙️ Advisor Appointment Scheduler")
        st.caption("Simulated voice agent — text-based. Theme-aware greeting uses latest pulse data.")

        # Pipeline stages
        st.markdown("**Pipeline:** `VAD → ASR → LLM → Tools → TTS` *(simulated — text-based for demo)*")

        if "voice_agent" not in st.session_state:
            top_theme = st.session_state.get("voice_top_theme", "general")
            from pillars.pillar_b_voice.voice_agent import VoiceAgent
            st.session_state["voice_agent"] = VoiceAgent(top_theme=top_theme)
            # Auto-greeting
            greeting = st.session_state["voice_agent"].process_turn("hello")
            if "voice_history" not in st.session_state:
                st.session_state["voice_history"] = []
            st.session_state["voice_history"].append({"role": "agent", "text": greeting["response"], "state": greeting["state"]})

        for entry in st.session_state.get("voice_history", []):
            role = entry.get("role")
            text = entry.get("text")
            state = entry.get("state", "")

            if role == "agent":
                st.markdown(f"🤖 **Agent** `[{state}]`")
                st.info(text)
            else:
                st.markdown(f"👤 **You:**")
                st.markdown(text)

        # User input
        user_input = st.text_input("Your response:", key="voice_input", placeholder="Type your response here...")

        if user_input:
            # Record user turn
            st.session_state["voice_history"].append({"role": "user", "text": user_input})

            # Process turn
            result = st.session_state["voice_agent"].process_turn(user_input)

            # Record agent response
            st.session_state["voice_history"].append({"role": "agent", "text": result["response"], "state": result["state"]})

            # Check for booking completion
            if result.get("booking_code"):
                st.success(f"✅ Booking confirmed! Code: **{result['booking_code']}**")
                st.session_state["booking_context"] = st.session_state["voice_agent"].get_booking_context()
                st.balloons()

            # Clear input and rerun
            st.session_state.pop("voice_input", None)
            st.rerun()

        # Reset button
        if st.button("🔄 Reset Voice Agent"):
            for key in ["voice_agent", "voice_history", "booking_context"]:
                st.session_state.pop(key, None)
            st.rerun()
