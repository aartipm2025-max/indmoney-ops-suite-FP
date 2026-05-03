import streamlit as st
import sys
import re
import time
import hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audio_recorder_streamlit import audio_recorder


def speak_text(text: str):
    """Convert text to speech using browser TTS."""
    clean_text = re.sub(r'\[.*?\]', '', text)
    clean_text = re.sub(r'[*_~`]', '', clean_text)
    clean_text = clean_text.replace('\n', '. ')
    clean_text = clean_text.replace('"', '\\"')

    st.markdown(f"""
    <script>
        var utterance = new SpeechSynthesisUtterance("{clean_text}");
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        // Use female voice if available
        var voices = window.speechSynthesis.getVoices();
        var femaleVoice = voices.find(v => v.name.includes('Female') || v.name.includes('Samantha') || v.name.includes('Google US English'));
        if (femaleVoice) {{
            utterance.voice = femaleVoice;
        }}

        window.speechSynthesis.speak(utterance);
    </script>
    """, unsafe_allow_html=True)


def render_tab_c():
    if "tab_c_initialized" not in st.session_state:
        st.session_state["tab_c_initialized"] = True
    st.header("Advisor Scheduler")
    st.caption("Book advisor consultations via voice or text. Theme-aware greetings based on latest pulse data.")

    # Prevent infinite loops
    if "voice_turn_count" not in st.session_state:
        st.session_state["voice_turn_count"] = 0

    # Reset if too many turns (safety)
    if st.session_state["voice_turn_count"] > 20:
        st.warning("Conversation limit reached. Starting fresh.")
        for key in ["voice_agent", "voice_history", "booking_context", "voice_turn_count"]:
            st.session_state.pop(key, None)
        st.rerun()

    # ── Pulse theme connection banner ─────────────────────────────────────────
    if "themes" in st.session_state and st.session_state["themes"]:
        top_theme = st.session_state["themes"][0].get("theme", "general")
        st.session_state["voice_top_theme"] = top_theme
        st.markdown(f"""
<div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px;
     padding: 10px 16px; margin-bottom: 16px; font-size: 13px; color: #92400E;
     display: flex; align-items: center; gap: 8px;">
    <span style="font-weight: 600; letter-spacing: 0.02em;">Connected to pulse theme:</span>
    <span style="background: #FEF3C7; padding: 2px 10px; border-radius: 12px;
          font-weight: 700; color: #78350F;">{top_theme}</span>
</div>
""", unsafe_allow_html=True)
    else:
        st.session_state.setdefault("voice_top_theme", "general")
        st.markdown("""
<div style="background: #F6F8FB; border: 1px solid #E8EDF3; border-radius: 6px;
     padding: 10px 16px; margin-bottom: 16px; font-size: 13px; color: #5A6C7D;">
    Generate a pulse in <strong>Weekly Pulse</strong> tab first for theme-aware greeting.
</div>
""", unsafe_allow_html=True)

    # Initialize voice agent
    if "voice_agent" not in st.session_state:
        top_theme = st.session_state.get("voice_top_theme", "general")
        from pillars.pillar_b_voice.voice_agent import VoiceAgent
        st.session_state["voice_agent"] = VoiceAgent(top_theme=top_theme)

        greeting = st.session_state["voice_agent"].process_turn("hello")
        if "voice_history" not in st.session_state:
            st.session_state["voice_history"] = []
        st.session_state["voice_history"].append({
            "role": "agent",
            "text": greeting["response"],
            "state": greeting["state"],
        })
        speak_text(greeting["response"])

    # ── Two-panel layout: conversation (left) + status (right) ───────────────
    chat_col, info_col = st.columns([3, 1])

    with info_col:
        history = st.session_state.get("voice_history", [])
        current_state = history[-1].get("state", "—") if history else "—"
        turn_count = st.session_state.get("voice_turn_count", 0)

        st.markdown(f"""
<div class="card" style="padding: 18px; margin-bottom: 12px;">
    <div class="section-label" style="margin-bottom: 10px;">Session State</div>
    <div style="font-size: 22px; font-weight: 700; color: #0B1F3A; margin-bottom: 6px;">
        {current_state or "INIT"}
    </div>
    <div style="font-size: 12px; color: #8A9BB0;">{turn_count} turn{"s" if turn_count != 1 else ""} completed</div>
</div>
""", unsafe_allow_html=True)

        # Progress steps
        steps = ["GREETING", "COLLECT_TOPIC", "COLLECT_SLOT", "CONFIRM", "DONE"]
        st.markdown('<div class="section-label">Progress</div>', unsafe_allow_html=True)
        for step in steps:
            is_done = current_state == "DONE" or (
                current_state and steps.index(step) < steps.index(current_state)
                if current_state in steps else False
            )
            is_active = current_state == step
            dot_color = "#10B981" if is_done else "#D4A437" if is_active else "#E8EDF3"
            text_color = "#0B1F3A" if (is_done or is_active) else "#8A9BB0"
            st.markdown(f"""
<div style="display: flex; align-items: center; gap: 8px; padding: 5px 0;">
    <span style="width: 8px; height: 8px; border-radius: 50%;
          background: {dot_color}; flex-shrink: 0; display: inline-block;"></span>
    <span style="font-size: 11px; font-weight: {'600' if is_active else '400'};
          color: {text_color}; letter-spacing: 0.04em;">{step}</span>
</div>
""", unsafe_allow_html=True)

    with chat_col:
        st.markdown('<div class="section-label">Conversation</div>', unsafe_allow_html=True)

        history = st.session_state.get("voice_history", [])
        latest_entry = history[-1] if history else None

        for entry in history:
            role = entry.get("role")
            text = entry.get("text")
            state = entry.get("state", "")

            if role == "agent":
                st.markdown(f"""
<div class="chat-agent">
    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
        <span style="font-size: 11px; font-weight: 700; color: #0B1F3A;
              letter-spacing: 0.06em; text-transform: uppercase;">Advisor Agent</span>
        <span style="background: #E8EDF3; color: #5A6C7D; padding: 1px 7px;
              border-radius: 4px; font-size: 10px; font-weight: 600;">{state}</span>
    </div>
    <div style="color: #2C3E50; font-size: 14px; line-height: 1.6;">{text}</div>
</div>
""", unsafe_allow_html=True)
                if entry is latest_entry:
                    speak_text(text)
            else:
                st.markdown(f"""
<div class="chat-user">
    <div style="margin-bottom: 6px;">
        <span style="font-size: 11px; font-weight: 700; color: #4F46E5;
              letter-spacing: 0.06em; text-transform: uppercase;">You</span>
    </div>
    <div style="color: #2C3E50; font-size: 14px; line-height: 1.6;">{text}</div>
</div>
""", unsafe_allow_html=True)

        # ── Input row ─────────────────────────────────────────────────────────
        st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
        inp_col, mic_col = st.columns([4, 1])

        with inp_col:
            text_input = st.text_input(
                "Message",
                key="voice_text_input",
                placeholder="Type your response here…",
                label_visibility="collapsed",
            )
            if st.button("Send", key="send_text", type="primary", use_container_width=True):
                if text_input:
                    st.session_state["voice_history"].append({"role": "user", "text": text_input})
                    result = st.session_state["voice_agent"].process_turn(text_input)
                    st.session_state["voice_history"].append({
                        "role": "agent",
                        "text": result["response"],
                        "state": result["state"],
                    })
                    if result.get("booking_code"):
                        st.session_state["booking_context"] = st.session_state["voice_agent"].get_booking_context()
                        speak_text(f"Booking confirmed! Your booking code is {result['booking_code']}")
                    st.session_state["voice_turn_count"] += 1
                    st.session_state.pop("voice_text_input", None)
                    time.sleep(0.5)
                    st.rerun()

        with mic_col:
            st.caption("Voice:")
            audio_bytes = audio_recorder(
                text="",
                recording_color="#D4A437",
                neutral_color="#0B1F3A",
                pause_threshold=2.5,
                sample_rate=16000,
            )

    # Process audio only when a genuinely new recording arrives.
    # audio_recorder holds the last bytes across reruns, so a boolean lock
    # always resets on rerun. A content hash is stable: same bytes → same
    # hash → skip; new recording → different hash → process once.
    if audio_bytes is not None:
        audio_hash = hashlib.md5(audio_bytes).hexdigest()
        if audio_hash != st.session_state.get("last_audio_hash"):
            st.session_state["last_audio_hash"] = audio_hash

            with st.spinner("Transcribing…"):
                try:
                    import tempfile
                    from groq import Groq

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", mode='wb') as f:
                        f.write(audio_bytes)
                        temp_path = f.name

                    client = Groq()
                    with open(temp_path, "rb") as audio_file:
                        trans = client.audio.transcriptions.create(
                            file=audio_file,
                            model="whisper-large-v3-turbo",
                        )

                    user_input = trans.text
                    st.session_state["voice_history"].append({"role": "user", "text": user_input})

                    result = st.session_state["voice_agent"].process_turn(user_input)
                    st.session_state["voice_history"].append({
                        "role": "agent",
                        "text": result["response"],
                        "state": result["state"],
                    })

                    if result.get("booking_code"):
                        st.session_state["booking_context"] = st.session_state["voice_agent"].get_booking_context()
                        speak_text(f"Booking confirmed! Your booking code is {result['booking_code']}")

                    st.session_state["voice_turn_count"] += 1
                    time.sleep(0.5)
                    st.rerun()

                except Exception as exc:
                    st.error(f"Audio error: {str(exc)}")

    # ── Booking confirmation card ─────────────────────────────────────────────
    if "booking_context" in st.session_state:
        bc = st.session_state["booking_context"]
        st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

        slot = bc.get("slot", {})
        st.markdown(f"""
<div class="card-green">
    <div style="display: flex; align-items: center; justify-content: space-between;
         margin-bottom: 16px;">
        <div>
            <div class="section-label" style="margin-bottom: 4px;">Booking Confirmed</div>
            <div style="font-size: 20px; font-weight: 700; color: #0B1F3A;
                 font-family: 'SF Mono', 'Fira Code', monospace; letter-spacing: 0.05em;">
                {bc.get("booking_code", "N/A")}
            </div>
        </div>
        <span class="status-pass">CONFIRMED</span>
    </div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
         background: #F6F8FB; border-radius: 6px; padding: 14px 16px;
         border: 1px solid #E8EDF3;">
        <div>
            <div style="font-size: 11px; color: #8A9BB0; font-weight: 700;
                 letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 3px;">Topic</div>
            <div style="font-size: 14px; font-weight: 500; color: #2C3E50;">{bc.get("topic", "N/A")}</div>
        </div>
        <div>
            <div style="font-size: 11px; color: #8A9BB0; font-weight: 700;
                 letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 3px;">Date</div>
            <div style="font-size: 14px; font-weight: 500; color: #2C3E50;">{slot.get("date", "N/A")}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

        st.markdown("### Action Required: Enter Your Email")
        st.caption("Your email will be shared with the advisor for meeting confirmation. No PII was collected during the call.")

        user_email = st.text_input(
            "Email address:",
            key="booking_email",
            placeholder="your.email@example.com",
        )
        if st.button("Complete Booking", type="primary", use_container_width=True):
            if user_email and "@" in user_email:
                st.session_state["booking_context"]["user_email"] = user_email
                st.success(f"Email saved: {user_email}")
                st.info("Go to the **Action Approval** tab to submit this booking to the advisor.")
                st.balloons()
            else:
                st.error("Please enter a valid email address.")

    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
    if st.button("Start New Conversation", use_container_width=True):
        for key in ["voice_agent", "voice_history", "booking_context", "voice_turn_count"]:
            st.session_state.pop(key, None)
        st.rerun()
