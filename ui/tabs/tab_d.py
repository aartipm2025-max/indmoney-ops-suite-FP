import streamlit as st
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def render_tab_d():
    if "tab_d_initialized" not in st.session_state:
        st.session_state["tab_d_initialized"] = True

    st.header("Action Approval")
    st.caption("Review and approve/reject MCP actions before they execute on Google services.")

    from pillars.pillar_c_hitl.approval import get_pending_ops, get_all_ops, approve, reject, REJECT_REASONS

    # Auto-submit booking to queue the moment this tab loads — no button needed.
    # submitted_bookings tracks which codes have been queued to prevent double-submit.
    if "submitted_bookings" not in st.session_state:
        st.session_state["submitted_bookings"] = set()

    if "booking_context" in st.session_state and "pulse" in st.session_state:
        bc = st.session_state["booking_context"]
        pulse = st.session_state["pulse"]
        booking_code = bc.get("booking_code", "N/A")

        if booking_code not in st.session_state["submitted_bookings"]:
            from pillars.pillar_c_hitl.mcp_tools import create_calendar_hold, create_email_draft, create_doc_append
            from pillars.pillar_c_hitl.briefing_card import generate_briefing_card, format_briefing_html, format_briefing_plain
            from pillars.pillar_c_hitl.approval import submit_for_approval
            from datetime import timedelta

            card = generate_briefing_card(pulse, bc)
            html = format_briefing_html(card)
            plain = format_briefing_plain(card)

            slot = bc.get("slot", {})
            slot_date = slot.get("date") or (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
            slot_time_str = slot.get("time", "10:00 AM IST").replace(" IST", "").strip()
            try:
                from datetime import datetime as _dt, timedelta as _td
                t = _dt.strptime(slot_time_str, "%I:%M %p")
                start = f"{slot_date}T{t.strftime('%H:%M:%S')}+05:30"
                end = f"{slot_date}T{(t + _td(minutes=30)).strftime('%H:%M:%S')}+05:30"
            except Exception:
                start = f"{slot_date}T10:00:00+05:30"
                end = f"{slot_date}T10:30:00+05:30"

            submit_for_approval(create_calendar_hold(
                f"Advisor Q&A — {bc.get('topic', 'General')} — {booking_code}",
                f"Booking: {booking_code}\n{plain}",
                start, end
            ), request_id=booking_code)

            submit_for_approval(create_email_draft(
                ["advisor@indmoney.demo"],
                f"Weekly Pulse + Briefing [{booking_code}]",
                html, plain, booking_code
            ), request_id=booking_code)

            submit_for_approval(create_doc_append(
                "Advisor Pre-Bookings",
                f"Date: {datetime.now(timezone.utc).isoformat()}\nBooking: {booking_code}\n{plain}",
                booking_code
            ), request_id=booking_code)

            st.session_state["submitted_bookings"].add(booking_code)
            st.toast(f"Booking {booking_code} sent to approval queue", icon="✅")

    elif "booking_context" in st.session_state and "pulse" not in st.session_state:
        st.warning("Booking found but no pulse data. Generate pulse first in the **Weekly Pulse** tab.")
    elif "pulse" not in st.session_state and "booking_context" not in st.session_state:
        st.markdown("""
<div style="padding: 12px 16px; background: #F6F8FB; border-radius: 6px;
     border: 1px solid #E8EDF3; font-size: 13px; color: #5A6C7D; margin-bottom: 16px;">
    Complete a booking in <strong>Voice Scheduler</strong> to see approval actions here.
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Pending Approvals ─────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Pending Approvals</div>', unsafe_allow_html=True)
    pending = get_pending_ops()

    if not pending:
        st.markdown("""
<div class="empty-state">
    <div class="empty-state-icon">✅</div>
    <h3>All caught up!</h3>
    <p>No pending operations requiring approval.</p>
</div>
""", unsafe_allow_html=True)
    else:
        import re
        from collections import defaultdict

        bookings = defaultdict(list)
        for op in pending:
            payload = op.get("payload", {}).get("payload", {})
            booking_code = payload.get("booking_code")
            if not booking_code:
                summary = payload.get("summary", "")
                subject = payload.get("subject", "")
                match = re.search(r'IND-[A-Z]{4}-\d{8}-\d{3}', summary + subject)
                booking_code = match.group(0) if match else "UNKNOWN"
            bookings[booking_code].append(op)

        for booking_code, ops in bookings.items():
            first_payload = ops[0].get("payload", {}).get("payload", {})

            if "summary" in first_payload:
                parts = first_payload["summary"].split(" — ")
                topic = parts[1] if len(parts) > 1 else "General Consultation"
                start_time = first_payload.get("start", "").replace("T", " ").split("+")[0]
            elif "subject" in first_payload:
                topic = "Advisor Briefing"
                start_time = "See calendar"
            else:
                topic = "Document Update"
                start_time = "N/A"

            st.markdown(f"""
<div class="hitl-op-card">
    <div style="display: flex; justify-content: space-between; align-items: flex-start;
         margin-bottom: 16px;">
        <div>
            <div style="font-size: 11px; font-weight: 700; color: #8A9BB0;
                 letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 6px;">
                Booking Request
            </div>
            <div style="font-size: 16px; font-weight: 700; color: #0B1F3A;
                 font-family: 'SF Mono', 'Fira Code', monospace; letter-spacing: 0.04em;">
                {booking_code}
            </div>
        </div>
        <span class="status-pending">Pending Review</span>
    </div>
    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;
         background: #F6F8FB; border-radius: 6px; padding: 14px 16px;
         border: 1px solid #E8EDF3; margin-bottom: 4px;">
        <div>
            <div style="font-size: 11px; color: #8A9BB0; font-weight: 700;
                 letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 3px;">Topic</div>
            <div style="font-size: 13px; font-weight: 500; color: #2C3E50;">{topic}</div>
        </div>
        <div>
            <div style="font-size: 11px; color: #8A9BB0; font-weight: 700;
                 letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 3px;">Scheduled</div>
            <div style="font-size: 13px; font-weight: 500; color: #2C3E50;">{start_time}</div>
        </div>
        <div>
            <div style="font-size: 11px; color: #8A9BB0; font-weight: 700;
                 letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 3px;">Actions</div>
            <div style="font-size: 13px; font-weight: 500; color: #2C3E50;">
                {len(ops)} &mdash; Calendar, Email, Doc
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button(
                    f"Approve All {len(ops)} Actions",
                    key=f"approve_all_{booking_code}",
                    type="primary",
                    use_container_width=True,
                ):
                    with st.spinner("Executing all actions…"):
                        results = [approve(op["id"]) for op in ops]
                        success_count = sum(1 for r in results if r.get("success"))
                        if success_count == len(ops):
                            st.success(f"All {len(ops)} actions executed successfully.")
                            st.balloons()
                        else:
                            st.warning(f"{success_count}/{len(ops)} actions succeeded.")
                        st.rerun()

            with col2:
                with st.popover("Reject All", use_container_width=True):
                    reason = st.selectbox(
                        "Reason:",
                        REJECT_REASONS,
                        key=f"reject_reason_{booking_code}",
                    )
                    reason_text = st.text_area(
                        "Details:",
                        key=f"reject_text_{booking_code}",
                        placeholder="Optional explanation…",
                    )
                    if st.button("Confirm Rejection", key=f"reject_confirm_{booking_code}"):
                        for op in ops:
                            reject(op["id"], reason, reason_text)
                        st.warning(f"Booking {booking_code} rejected.")
                        st.rerun()

            with st.expander("View Technical Details", expanded=False):
                for i, op in enumerate(ops, 1):
                    st.caption(f"Action {i}: {op['op_type']}")
                    st.json(op.get("payload", {}), expanded=False)

            st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

    # ── Operation History ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-label">Operation History</div>', unsafe_allow_html=True)

    all_ops = get_all_ops()
    if all_ops:
        _badge_map = {
            "pending":  "status-pending",
            "approved": "status-approved",
            "executed": "status-pass",
            "failed":   "status-fail",
            "rejected": "status-rejected",
        }
        st.markdown("""
<div style="background: #FFFFFF; border-radius: 8px; border: 1px solid #E8EDF3;
     overflow: hidden; box-shadow: 0 1px 3px rgba(11,31,58,0.04);">
""", unsafe_allow_html=True)
        for i, op in enumerate(all_ops):
            badge_cls = _badge_map.get(op["status"], "status-pending")
            row_bg = "#FFFFFF" if i % 2 == 0 else "#FAFBFC"
            st.markdown(f"""
<div style="display: flex; align-items: center; gap: 14px;
     padding: 11px 16px; background: {row_bg};
     border-bottom: 1px solid #F0F3F6; font-size: 13px;">
    <span class="{badge_cls}">{op["status"]}</span>
    <span style="color: #0B1F3A; font-weight: 500; flex: 1;">{op["op_type"]}</span>
    <span style="color: #8A9BB0; font-size: 12px; font-family: 'SF Mono', monospace;">
        {op.get("created_at", "")[:19]}
    </span>
</div>
""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="padding: 24px; color: #8A9BB0; font-size: 13px; text-align: center;
     background: #FFFFFF; border-radius: 8px; border: 1px solid #E8EDF3;">
    No operations recorded yet.
</div>
""", unsafe_allow_html=True)
