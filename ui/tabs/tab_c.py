import streamlit as st
import sys
import re
import time
import hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audio_recorder_streamlit import audio_recorder


_CSS = """
<style>
/* ── Advisor Scheduler Workspace ──────────────────────────────────────── */

.vc-context {
    display:flex; align-items:center; gap:10px; flex-wrap:wrap;
    padding:9px 16px; border-radius:8px;
    border:1px solid #E8EDF3; background:#FAFBFC;
    margin-bottom:20px;
}
.vc-context-label {
    font-size:10px; font-weight:700; letter-spacing:0.08em;
    text-transform:uppercase; color:#9CA3AF;
}
.vc-context-val {
    font-size:12px; font-weight:600; color:#0B1F3A;
}
.vc-context-sep { color:#D1D5DB; }

/* AI message */
.vc-msg-ai {
    background:#FFFFFF;
    border:1px solid #E8EDF3;
    border-left:3px solid #0B1F3A;
    border-radius:2px 10px 10px 2px;
    padding:14px 18px;
    margin-bottom:12px;
    transition:box-shadow 0.15s;
}
.vc-msg-ai:hover { box-shadow:0 3px 12px rgba(11,31,58,0.07); }
.vc-msg-ai-header {
    display:flex; align-items:center; gap:8px; margin-bottom:8px;
}
.vc-msg-ai-name {
    font-size:10px; font-weight:700; letter-spacing:0.09em;
    text-transform:uppercase; color:#0B1F3A;
}
.vc-msg-state {
    font-size:9px; font-weight:700; letter-spacing:0.06em;
    text-transform:uppercase; background:#EEF2FF; color:#5B7CFA;
    padding:2px 7px; border-radius:3px;
}
.vc-msg-body {
    font-size:14px; color:#1B2430; line-height:1.7;
}

/* User message */
.vc-msg-user {
    background:#EEF2FF;
    border:1px solid #C7D2FE;
    border-right:3px solid #5B7CFA;
    border-radius:10px 2px 2px 10px;
    padding:12px 16px;
    margin-bottom:12px;
    margin-left:56px;
}
.vc-msg-user-header {
    display:flex; align-items:center; justify-content:flex-end;
    margin-bottom:6px;
}
.vc-msg-user-name {
    font-size:10px; font-weight:700; letter-spacing:0.09em;
    text-transform:uppercase; color:#4F46E5;
}
.vc-msg-user-body {
    font-size:14px; color:#312E81; line-height:1.65;
}

/* Status panel */
.vc-panel {
    background:#FFFFFF; border:1px solid #E8EDF3;
    border-radius:10px; padding:18px 16px; margin-bottom:12px;
}
.vc-panel-title {
    font-size:10px; font-weight:700; letter-spacing:0.09em;
    text-transform:uppercase; color:#9CA3AF; margin-bottom:12px;
}
.vc-state-val {
    font-size:15px; font-weight:700;
    font-family:'SF Mono','Fira Code',monospace;
    letter-spacing:0.04em; margin-bottom:4px;
}
.vc-state-sub { font-size:11px; color:#9CA3AF; }

/* Vertical stepper */
.vc-stepper { display:flex; flex-direction:column; }
.vc-step { display:flex; align-items:flex-start; gap:10px; }
.vc-step-left {
    display:flex; flex-direction:column; align-items:center;
    width:16px; flex-shrink:0;
}
.vc-step-dot {
    width:15px; height:15px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:8px; font-weight:700; flex-shrink:0;
}
.vc-dot-done   { background:#0B1F3A; color:#FFFFFF; }
.vc-dot-active { background:#5B7CFA; color:#FFFFFF;
    box-shadow:0 0 0 3px rgba(91,124,250,0.20); }
.vc-dot-pending { background:#FFFFFF; border:2px solid #E8EDF3; color:#D1D5DB; }
.vc-step-line  { width:1px; flex:1; min-height:14px; background:#E8EDF3; margin:2px 0; }
.vc-line-done  { background:#0B1F3A; }
.vc-step-content { padding:0 0 14px 2px; }
.vc-slabel-done    { font-size:11px; font-weight:600; color:#0B1F3A; }
.vc-slabel-active  { font-size:11px; font-weight:700; color:#5B7CFA; }
.vc-slabel-pending { font-size:11px; font-weight:400; color:#9CA3AF; }
.vc-step-sub { font-size:10px; color:#9CA3AF; margin-top:1px; }


/* Booking card */
.vc-booking {
    background:#0B1F3A; border-radius:12px;
    padding:24px 26px; margin-top:20px;
}
.vc-booking-eyebrow {
    font-size:10px; font-weight:700; letter-spacing:0.10em;
    text-transform:uppercase; color:#5B7CFA; margin-bottom:6px;
}
.vc-booking-code {
    font-size:20px; font-weight:700; color:#FFFFFF;
    font-family:'SF Mono','Fira Code',monospace;
    letter-spacing:0.05em; margin-bottom:16px;
}
.vc-booking-grid {
    display:grid; grid-template-columns:1fr 1fr; gap:12px;
    background:rgba(255,255,255,0.07); border-radius:8px;
    padding:14px 16px; margin-bottom:14px;
}
.vc-booking-fl {
    font-size:10px; font-weight:700; letter-spacing:0.07em;
    text-transform:uppercase; color:rgba(255,255,255,0.45); margin-bottom:3px;
}
.vc-booking-fv { font-size:13px; font-weight:500; color:#FFFFFF; }
.vc-booking-email {
    font-size:12px; color:rgba(255,255,255,0.55);
}
.vc-booking-email strong { color:rgba(255,255,255,0.90); }
</style>
"""


def speak_text(text: str):
    clean = re.sub(r'\[.*?\]', '', text)
    clean = re.sub(r'[*_~`]', '', clean)
    clean = clean.replace('\n', '. ').replace('"', '\\"')
    st.markdown(f"""
    <script>
        var u = new SpeechSynthesisUtterance("{clean}");
        u.rate = 1.0; u.pitch = 1.0; u.volume = 1.0;
        var voices = window.speechSynthesis.getVoices();
        var fv = voices.find(v => v.name.includes('Female') || v.name.includes('Samantha') || v.name.includes('Google US English'));
        if (fv) {{ u.voice = fv; }}
        window.speechSynthesis.speak(u);
    </script>
    """, unsafe_allow_html=True)


def _stepper_html(steps, current_state):
    meta = {
        "GREETING":      ("Greeting",     "Opening session"),
        "COLLECT_TOPIC": ("Topic",         "Capture your need"),
        "COLLECT_SLOT":  ("Schedule",      "Pick date & time"),
        "CONFIRM":       ("Confirm",       "Review details"),
        "DONE":          ("Complete",      "Booking confirmed"),
    }
    html = '<div class="vc-stepper">'
    for i, step in enumerate(steps):
        is_last = i == len(steps) - 1
        is_done = (current_state == "DONE") or (
            current_state in steps and steps.index(step) < steps.index(current_state)
        )
        is_active = current_state == step

        if is_done:
            dot_cls, dot_char, lbl_cls, line_cls = "vc-dot-done", "✓", "vc-slabel-done", "vc-line-done"
        elif is_active:
            dot_cls, dot_char, lbl_cls, line_cls = "vc-dot-active", str(i+1), "vc-slabel-active", ""
        else:
            dot_cls, dot_char, lbl_cls, line_cls = "vc-dot-pending", str(i+1), "vc-slabel-pending", ""

        label, sub = meta.get(step, (step, ""))
        line_html = "" if is_last else f'<div class="vc-step-line {line_cls}"></div>'
        html += f"""
<div class="vc-step">
  <div class="vc-step-left">
    <div class="vc-step-dot {dot_cls}">{dot_char}</div>
    {line_html}
  </div>
  <div class="vc-step-content">
    <div class="{lbl_cls}">{label}</div>
    <div class="vc-step-sub">{sub}</div>
  </div>
</div>"""
    html += '</div>'
    return html


def render_tab_c():
    st.markdown(_CSS, unsafe_allow_html=True)

    if "tab_c_initialized" not in st.session_state:
        st.session_state["tab_c_initialized"] = True

    # Safety guard (unchanged)
    if "voice_turn_count" not in st.session_state:
        st.session_state["voice_turn_count"] = 0
    if st.session_state["voice_turn_count"] > 20:
        st.warning("Conversation limit reached. Starting fresh.")
        for key in ["voice_agent", "voice_history", "booking_context", "voice_turn_count"]:
            st.session_state.pop(key, None)
        st.rerun()

    # Pulse theme detection (unchanged logic)
    if "themes" in st.session_state and st.session_state["themes"]:
        top_theme = st.session_state["themes"][0].get("name", "general")
        st.session_state["voice_top_theme"] = top_theme
        pulse_label = top_theme
        pulse_color = "#10B981"
    else:
        st.session_state.setdefault("voice_top_theme", "general")
        pulse_label = "Not connected"
        pulse_color = "#9CA3AF"

    # Initialize voice agent (unchanged logic)
    if "voice_agent" not in st.session_state:
        from pillars.pillar_b_voice.voice_agent import VoiceAgent
        st.session_state["voice_agent"] = VoiceAgent(
            top_theme=st.session_state.get("voice_top_theme", "general")
        )
        greeting = st.session_state["voice_agent"].process_turn("hello")
        st.session_state.setdefault("voice_history", [])
        st.session_state["voice_history"].append({
            "role": "agent", "text": greeting["response"], "state": greeting["state"],
        })
        speak_text(greeting["response"])

    # Derive current state
    history      = st.session_state.get("voice_history", [])
    latest_entry = history[-1] if history else None
    current_state = (
        latest_entry.get("state", "GREETING")
        if latest_entry and latest_entry.get("role") == "agent"
        else "GREETING"
    )
    turn_count = st.session_state.get("voice_turn_count", 0)
    steps = ["GREETING", "COLLECT_TOPIC", "COLLECT_SLOT", "CONFIRM", "DONE"]

    # Context bar
    st.markdown(f"""
<div class="vc-context">
  <span style="width:7px;height:7px;border-radius:50%;background:{pulse_color};
       display:inline-block;flex-shrink:0;
       box-shadow:0 0 0 3px rgba(16,185,129,0.15);"></span>
  <span class="vc-context-label">Pulse Theme</span>
  <span class="vc-context-val">{pulse_label}</span>
  <span class="vc-context-sep">&nbsp;|&nbsp;</span>
  <span class="vc-context-label">Turns</span>
  <span class="vc-context-val">{turn_count}</span>
  <span class="vc-context-sep">&nbsp;|&nbsp;</span>
  <span class="vc-context-label">State</span>
  <span class="vc-context-val">{current_state}</span>
</div>
""", unsafe_allow_html=True)

    # ── Main workspace ────────────────────────────────────────────────────────
    chat_col, status_col = st.columns([7, 3], gap="large")

    with status_col:
        state_color = "#10B981" if current_state == "DONE" else "#5B7CFA"
        st.markdown(f"""
<div class="vc-panel">
  <div class="vc-panel-title">Session Status</div>
  <div class="vc-state-val" style="color:{state_color};">{current_state or "INIT"}</div>
  <div class="vc-state-sub">{turn_count} turn{"s" if turn_count != 1 else ""} &nbsp;·&nbsp; Ready</div>
</div>
""", unsafe_allow_html=True)

        st.markdown(f"""
<div class="vc-panel">
  <div class="vc-panel-title">Workflow Progress</div>
  {_stepper_html(steps, current_state)}
</div>
""", unsafe_allow_html=True)

        if st.button("New Session", use_container_width=True, key="new_session_btn"):
            for key in ["voice_agent", "voice_history", "booking_context", "voice_turn_count"]:
                st.session_state.pop(key, None)
            st.rerun()

    with chat_col:
        st.markdown(
            '<div class="section-label" style="margin-bottom:14px;">Conversation</div>',
            unsafe_allow_html=True,
        )

        # Message history
        for entry in history:
            role = entry.get("role")
            text = entry.get("text", "")
            state = entry.get("state", "")

            if role == "agent":
                state_badge = f'<span class="vc-msg-state">{state}</span>' if state else ""
                st.markdown(f"""
<div class="vc-msg-ai">
  <div class="vc-msg-ai-header">
    <span class="vc-msg-ai-name">Advisor AI</span>
    {state_badge}
  </div>
  <div class="vc-msg-body">{text}</div>
</div>
""", unsafe_allow_html=True)
                if entry is latest_entry:
                    speak_text(text)
            else:
                st.markdown(f"""
<div class="vc-msg-user">
  <div class="vc-msg-user-header">
    <span class="vc-msg-user-name">You</span>
  </div>
  <div class="vc-msg-user-body">{text}</div>
</div>
""", unsafe_allow_html=True)

        # Input row: text | mic | send
        st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
        inp_col, mic_col, btn_col = st.columns([5, 1, 1])
        with inp_col:
            text_input = st.text_input(
                "Message",
                key="voice_text_input",
                placeholder="Type your message…",
                label_visibility="collapsed",
            )
        with mic_col:
            audio_bytes = audio_recorder(
                text="",
                recording_color="#5B7CFA",
                neutral_color="#0B1F3A",
                pause_threshold=2.5,
                sample_rate=16000,
            )
        with btn_col:
            send_clicked = st.button(
                "Send", key="send_text", type="primary", use_container_width=True
            )

        if send_clicked and text_input:
            st.session_state["voice_history"].append({"role": "user", "text": text_input})
            result = st.session_state["voice_agent"].process_turn(text_input)
            st.session_state["voice_history"].append({
                "role": "agent", "text": result["response"], "state": result["state"],
            })
            if result.get("booking_code"):
                st.session_state["booking_context"] = (
                    st.session_state["voice_agent"].get_booking_context()
                )
                speak_text(f"Booking confirmed! Your booking code is {result['booking_code']}")
            st.session_state["voice_turn_count"] += 1
            st.session_state.pop("voice_text_input", None)
            time.sleep(0.5)
            st.rerun()

    # ── Audio processing (unchanged logic) ───────────────────────────────────
    if audio_bytes is not None:
        audio_hash = hashlib.md5(audio_bytes).hexdigest()
        if audio_hash != st.session_state.get("last_audio_hash"):
            st.session_state["last_audio_hash"] = audio_hash
            with st.spinner("Transcribing…"):
                try:
                    import tempfile
                    from groq import Groq
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", mode="wb") as f:
                        f.write(audio_bytes)
                        temp_path = f.name
                    client = Groq()
                    with open(temp_path, "rb") as af:
                        trans = client.audio.transcriptions.create(
                            file=af, model="whisper-large-v3-turbo"
                        )
                    user_input = trans.text
                    st.session_state["voice_history"].append({"role": "user", "text": user_input})
                    result = st.session_state["voice_agent"].process_turn(user_input)
                    st.session_state["voice_history"].append({
                        "role": "agent", "text": result["response"], "state": result["state"],
                    })
                    if result.get("booking_code"):
                        st.session_state["booking_context"] = (
                            st.session_state["voice_agent"].get_booking_context()
                        )
                        speak_text(f"Booking confirmed! Your booking code is {result['booking_code']}")
                    st.session_state["voice_turn_count"] += 1
                    time.sleep(0.5)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Audio error: {str(exc)}")

    # ── Booking confirmation card ─────────────────────────────────────────────
    if "booking_context" in st.session_state:
        bc = st.session_state["booking_context"]
        slot = bc.get("slot", {})
        user_email = st.session_state.get("email", "")

        st.markdown(f"""
<div class="vc-booking">
  <div class="vc-booking-eyebrow">Booking Confirmed</div>
  <div class="vc-booking-code">{bc.get("booking_code", "N/A")}</div>
  <div class="vc-booking-grid">
    <div>
      <div class="vc-booking-fl">Topic</div>
      <div class="vc-booking-fv">{bc.get("topic", "N/A")}</div>
    </div>
    <div>
      <div class="vc-booking-fl">Date</div>
      <div class="vc-booking-fv">{slot.get("date", "N/A")}</div>
    </div>
  </div>
  <div class="vc-booking-email">Confirmation for <strong>{user_email}</strong></div>
</div>
""", unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("Complete Booking", type="primary", use_container_width=True):
            st.session_state["booking_context"]["user_email"] = user_email
            st.success(f"Booking confirmed for {user_email}")
            st.info("Go to the **Action Approval** tab to submit this booking to the advisor.")
            st.balloons()
