import streamlit as st
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def render_tab_d():
    st.header("✅ HITL Approval Center")
    st.caption("Review and approve/reject MCP actions before they execute on Google services.")

    from pillars.pillar_c_hitl.approval import get_pending_ops, get_all_ops, approve, reject, REJECT_REASONS

    # Check for completed booking from Voice tab
    if "booking_context" in st.session_state and "pulse" in st.session_state:
        bc = st.session_state["booking_context"]
        pulse = st.session_state["pulse"]
        booking_code = bc.get("booking_code", "N/A")

        st.success(f"📋 New booking ready: **{booking_code}**")

        if st.button("🚀 Submit Calendar + Email + Doc to Approval Queue", type="primary", use_container_width=True, key="submit_mcp"):
            from pillars.pillar_c_hitl.mcp_tools import create_calendar_hold, create_email_draft, create_doc_append
            from pillars.pillar_c_hitl.briefing_card import generate_briefing_card, format_briefing_html, format_briefing_plain
            from pillars.pillar_c_hitl.approval import submit_for_approval

            # Generate briefing
            card = generate_briefing_card(pulse, bc)
            html = format_briefing_html(card)
            plain = format_briefing_plain(card)

            # Get slot details
            slot = bc.get("slot", {})
            start = slot.get("date", "2026-04-28") + "T10:00:00+05:30"
            end = slot.get("date", "2026-04-28") + "T10:30:00+05:30"

            # Submit 3 MCP actions
            op1 = submit_for_approval(create_calendar_hold(
                f"Advisor Q&A — {bc.get('topic', 'General')} — {booking_code}",
                f"Booking: {booking_code}\n{plain}",
                start, end
            ))

            op2 = submit_for_approval(create_email_draft(
                ["advisor@indmoney.demo"],
                f"Weekly Pulse + Briefing [{booking_code}]",
                html, plain, booking_code
            ))

            op3 = submit_for_approval(create_doc_append(
                "Advisor Pre-Bookings",
                f"Date: {datetime.now(timezone.utc).isoformat()}\nBooking: {booking_code}\n{plain}",
                booking_code
            ))

            st.success(f"✅ 3 actions submitted to queue!")
            st.balloons()
            st.rerun()

    elif "booking_context" in st.session_state and "pulse" not in st.session_state:
        st.warning("⚠️ Booking found but no pulse data. Generate pulse first in **Weekly Pulse** tab.")

    elif "pulse" in st.session_state and "booking_context" not in st.session_state:
        st.info("💡 Complete a booking in **Voice Scheduler** tab to submit actions for approval.")

    else:
        st.info("💡 Generate pulse and complete booking to see approval actions.")

    st.markdown("---")

    st.subheader("⏳ Pending Approvals")
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
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 16px;">
                    <div>
                        <h3 style="color: #0B1F3A; margin: 0 0 8px 0;">&#x1F4C5; New Booking Request</h3>
                        <p style="color: #5A6C7D; margin: 0;"><strong>Code:</strong> {booking_code}</p>
                    </div>
                    <span class="status-pending">PENDING</span>
                </div>
                <div style="background: #F6F8FB; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                    <p style="margin: 4px 0;"><strong>Topic:</strong> {topic}</p>
                    <p style="margin: 4px 0;"><strong>Scheduled:</strong> {start_time}</p>
                    <p style="margin: 4px 0;"><strong>Actions:</strong> {len(ops)} pending (Calendar + Email + Doc)</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button(
                    f"✅ Approve All {len(ops)} Actions",
                    key=f"approve_all_{booking_code}",
                    type="primary",
                    use_container_width=True
                ):
                    with st.spinner("Executing all actions..."):
                        results = [approve(op["id"]) for op in ops]
                        success_count = sum(1 for r in results if r.get("success"))
                        if success_count == len(ops):
                            st.success(f"✅ All {len(ops)} actions executed successfully!")
                            st.balloons()
                        else:
                            st.warning(f"⚠️ {success_count}/{len(ops)} actions succeeded")
                        st.rerun()

            with col2:
                with st.popover("❌ Reject All", use_container_width=True):
                    reason = st.selectbox(
                        "Reason:",
                        REJECT_REASONS,
                        key=f"reject_reason_{booking_code}"
                    )
                    reason_text = st.text_area(
                        "Details:",
                        key=f"reject_text_{booking_code}",
                        placeholder="Optional explanation..."
                    )
                    if st.button("Confirm Rejection", key=f"reject_confirm_{booking_code}"):
                        for op in ops:
                            reject(op["id"], reason, reason_text)
                        st.warning(f"🗑️ Booking {booking_code} rejected")
                        st.rerun()

            with st.expander("🔍 View Technical Details", expanded=False):
                for i, op in enumerate(ops, 1):
                    st.caption(f"Action {i}: {op['op_type']}")
                    st.json(op.get("payload", {}), expanded=False)

            st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Operation History")
    all_ops = get_all_ops()
    if all_ops:
        for op in all_ops:
            status_emoji = {"pending": "🔶", "approved": "🔵", "executed": "🟢", "failed": "🔴", "rejected": "⚫"}.get(op["status"], "⚪")
            st.markdown(f"{status_emoji} **{op['op_type']}** — {op['status']} — {op.get('created_at', '')[:19]}")
    else:
        st.caption("No operations recorded yet.")
