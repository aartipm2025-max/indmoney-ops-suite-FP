import streamlit as st
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def render_tab_c():
    st.header("✅ HITL Approval Center")
    st.caption("Review and approve/reject MCP actions before they execute on Google services.")

    from pillars.pillar_c_hitl.approval import get_pending_ops, get_all_ops, approve, reject, REJECT_REASONS

    # Submit actions from voice booking
    if "booking_context" in st.session_state and "pulse" in st.session_state:
        bc = st.session_state["booking_context"]
        pulse = st.session_state["pulse"]
        booking_code = bc.get("booking_code", "N/A")

        with st.expander(f"📝 Generate MCP Actions for booking {booking_code}", expanded=True):
            if st.button("Submit Calendar + Email + Doc to HITL Queue", key="submit_hitl"):
                from pillars.pillar_c_hitl.mcp_tools import create_calendar_hold, create_email_draft, create_doc_append
                from pillars.pillar_c_hitl.briefing_card import generate_briefing_card, format_briefing_html, format_briefing_plain

                card = generate_briefing_card(pulse, bc)
                html = format_briefing_html(card)
                plain = format_briefing_plain(card)

                slot = bc.get("slot", {})
                start = slot.get("date", "2026-04-28") + "T10:00:00+05:30"
                end = slot.get("date", "2026-04-28") + "T10:30:00+05:30"

                from pillars.pillar_c_hitl.approval import submit_for_approval

                op1 = submit_for_approval(create_calendar_hold(
                    f"Advisor Q&A — {bc.get('topic', 'General')} — {booking_code}",
                    f"Booking: {booking_code}\n{plain}", start, end))
                op2 = submit_for_approval(create_email_draft(
                    ["advisor@indmoney.demo"],
                    f"Weekly Pulse + Briefing [{booking_code}]",
                    html, plain, booking_code))
                op3 = submit_for_approval(create_doc_append(
                    "Advisor Pre-Bookings",
                    f"Date: {datetime.now(timezone.utc).isoformat()}\nBooking: {booking_code}\nTopic: {bc.get('topic')}\n{plain}",
                    booking_code))

                st.success(f"✅ 3 actions submitted: {op1}, {op2}, {op3}")
                st.rerun()
    else:
        st.info("💡 Generate a pulse (Tab B) and complete a voice booking first to create HITL actions.")

    st.markdown("---")

    # Pending operations
    st.subheader("Pending Approvals")
    pending = get_pending_ops()

    if not pending:
        st.info("No pending operations.")
    else:
        for op in pending:
            with st.expander(f"🔶 {op['op_type']} — {op['id']}", expanded=True):
                payload = op.get("payload", {})
                st.json(payload)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✅ Approve", key=f"approve_{op['id']}"):
                        result = approve(op["id"])
                        if result.get("success"):
                            st.success(f"Executed! {json.dumps({k: v for k, v in result.items() if k != 'success'})}")
                        else:
                            st.error(f"Failed: {result.get('error', 'Unknown')}")
                        st.rerun()

                with col2:
                    reason = st.selectbox("Reject reason:", REJECT_REASONS, key=f"reason_{op['id']}")
                    reason_text = st.text_input("Details:", key=f"reason_text_{op['id']}")
                    if st.button(f"❌ Reject", key=f"reject_{op['id']}"):
                        result = reject(op["id"], reason, reason_text)
                        if result.get("success"):
                            st.warning("Rejected and logged.")
                        st.rerun()

    # All operations history
    st.markdown("---")
    st.subheader("Operation History")
    all_ops = get_all_ops()
    if all_ops:
        for op in all_ops:
            status_emoji = {"pending": "🔶", "approved": "🔵", "executed": "🟢", "failed": "🔴", "rejected": "⚫"}.get(op["status"], "⚪")
            st.markdown(f"{status_emoji} **{op['op_type']}** — {op['status']} — {op.get('created_at', '')[:19]}")
    else:
        st.caption("No operations recorded yet.")
