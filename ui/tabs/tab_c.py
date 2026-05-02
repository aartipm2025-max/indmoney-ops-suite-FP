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
    st.header("🎙️ AI Advisor Scheduler")
    st.caption("Book advisor consultations via voice or text. Theme-aware greetings based on latest pulse data.")

    # Prevent infinite loops
    if "voice_turn_count" not in st.session_state:
        st.session_state["voice_turn_count"] = 0

    # Reset if too many turns (safety)
    if st.session_state["voice_turn_count"] > 20:
        st.warning("⚠️ Conversation limit reached. Starting fresh.")
        for key in ["voice_agent", "voice_history", "booking_context", "voice_turn_count"]:
            st.session_state.pop(key, None)
        st.rerun()

    # Connect to pulse theme
    if "themes" in st.session_state and st.session_state["themes"]:
        top_theme = st.session_state["themes"][0].get("theme", "general")
        st.session_state["voice_top_theme"] = top_theme
        st.info(f"🎯 Connected to pulse theme: **{top_theme}**")
    else:
        st.session_state.setdefault("voice_top_theme", "general")
        st.warning("💡 Generate a pulse in **Weekly Pulse** tab first for theme-aware greeting")

    # Initialize voice agent
    if "voice_agent" not in st.session_state:
        top_theme = st.session_state.get("voice_top_theme", "general")
        from pillars.pillar_b_voice.voice_agent import VoiceAgent
        st.session_state["voice_agent"] = VoiceAgent(top_theme=top_theme)

        # Auto-greeting
        greeting = st.session_state["voice_agent"].process_turn("hello")
        if "voice_history" not in st.session_state:
            st.session_state["voice_history"] = []
        st.session_state["voice_history"].append({
            "role": "agent",
            "text": greeting["response"],
            "state": greeting["state"]
        })

        # AUTO-SPEAK GREETING
        speak_text(greeting["response"])

    # Conversation display
    st.markdown("### 💬 Conversation")

    history = st.session_state.get("voice_history", [])
    latest_entry = history[-1] if history else None

    for entry in history:
        role = entry.get("role")
        text = entry.get("text")
        state = entry.get("state", "")

        if role == "agent":
            st.markdown(f"""
            <div style="background: #F0F4F8; border-radius: 12px; padding: 20px; margin-bottom: 16px; border-left: 4px solid #0B1F3A;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                    <span style="font-size: 24px;">🤖</span>
                    <div>
                        <strong style="color: #0B1F3A;">Agent</strong>
                        <span style="background: #E8EDF3; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-left: 8px;">{state}</span>
                    </div>
                </div>
                <div style="color: #2C3E50;">{text}</div>
            </div>
            """, unsafe_allow_html=True)

            # Speak only the latest agent message
            if entry is latest_entry:
                speak_text(text)
        else:
            st.markdown(f"""
            <div style="background: #E8F0FE; border-radius: 12px; padding: 20px; margin-bottom: 16px; margin-left: 40px; border-left: 4px solid #4285F4;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                    <span style="font-size: 24px;">👤</span>
                    <strong style="color: #0B1F3A;">You</strong>
                </div>
                <div style="color: #2C3E50;">{text}</div>
            </div>
            """, unsafe_allow_html=True)

    # Input section
    st.markdown("---")
    st.markdown("### 💬 Your Response")

    col1, col2 = st.columns([3, 1])

    with col1:
        text_input = st.text_input(
            "Type your message:",
            key="voice_text_input",
            placeholder="Type here or use microphone...",
            label_visibility="collapsed"
        )
        if st.button("Send", key="send_text", type="primary", use_container_width=True):
            if text_input:
                st.session_state["voice_history"].append({"role": "user", "text": text_input})
                result = st.session_state["voice_agent"].process_turn(text_input)
                st.session_state["voice_history"].append({
                    "role": "agent",
                    "text": result["response"],
                    "state": result["state"]
                })
                if result.get("booking_code"):
                    st.session_state["booking_context"] = st.session_state["voice_agent"].get_booking_context()
                    speak_text(f"Booking confirmed! Your booking code is {result['booking_code']}")
                st.session_state["voice_turn_count"] += 1
                st.session_state.pop("voice_text_input", None)
                time.sleep(0.5)
                st.rerun()

    with col2:
        st.caption("Or speak:")
        audio_bytes = audio_recorder(
            text="🎤",
            recording_color="#D4A437",
            neutral_color="#0B1F3A",
            pause_threshold=2.5,
            sample_rate=16000
        )

    # Process audio only when a genuinely new recording arrives.
    # audio_recorder holds the last bytes across reruns, so a boolean lock
    # always resets on rerun. A content hash is stable: same bytes → same
    # hash → skip; new recording → different hash → process once.
    if audio_bytes is not None:
        audio_hash = hashlib.md5(audio_bytes).hexdigest()
        if audio_hash != st.session_state.get("last_audio_hash"):
            st.session_state["last_audio_hash"] = audio_hash

            with st.spinner("🎧 Transcribing..."):
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
                            model="whisper-large-v3-turbo"
                        )

                    user_input = trans.text
                    st.session_state["voice_history"].append({"role": "user", "text": user_input})

                    result = st.session_state["voice_agent"].process_turn(user_input)
                    st.session_state["voice_history"].append({
                        "role": "agent",
                        "text": result["response"],
                        "state": result["state"]
                    })

                    if result.get("booking_code"):
                        st.session_state["booking_context"] = st.session_state["voice_agent"].get_booking_context()
                        speak_text(f"Booking confirmed! Your booking code is {result['booking_code']}")

                    st.session_state["voice_turn_count"] += 1
                    time.sleep(0.5)
                    st.rerun()

                except Exception as exc:
                    st.error(f"Audio error: {str(exc)}")

    # Booking confirmation
    if "booking_context" in st.session_state:
        bc = st.session_state["booking_context"]
        st.markdown("---")
        st.success("✅ Booking Confirmed!")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Booking Code", bc.get("booking_code", "N/A"))
        with col2:
            st.metric("Topic", bc.get("topic", "N/A"))
        with col3:
            slot = bc.get("slot", {})
            st.metric("Date", slot.get("date", "N/A"))

        st.markdown("### ✉️ Action Required: Enter Your Email")
        st.caption("Your email will be shared with the advisor for meeting confirmation. No PII was collected during the call.")

        user_email = st.text_input(
            "Email address:",
            key="booking_email",
            placeholder="your.email@example.com"
        )
        if st.button("📧 Complete Booking", type="primary", use_container_width=True):
            if user_email and "@" in user_email:
                st.session_state["booking_context"]["user_email"] = user_email
                st.success(f"✅ Email saved: {user_email}")
                st.info("💡 Go to **Action Approval** tab to submit this booking to the advisor.")
                st.balloons()
            else:
                st.error("❌ Please enter a valid email address")

    if st.button("🔄 Start New Conversation", use_container_width=True):
        for key in ["voice_agent", "voice_history", "booking_context", "voice_turn_count"]:
            st.session_state.pop(key, None)
        st.rerun()
