import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pytest

def test_voice_agent_uses_pulse_theme():
    """Voice agent greeting mentions the top theme from pulse."""
    from pillars.pillar_b_voice.voice_agent import VoiceAgent
    agent = VoiceAgent(top_theme="Technical Issues")
    result = agent.process_turn("hello")
    assert "Technical Issues" in result["response"]

def test_booking_code_in_mcp_payloads():
    """Booking code propagates to all 3 MCP tool payloads."""
    from pillars.pillar_c_hitl.mcp_tools import create_calendar_hold, create_email_draft, create_doc_append
    import json
    code = "IND-TECH-20260428-001"
    cal = create_calendar_hold("Test", f"Code: {code}", "2026-04-28T10:00:00+05:30", "2026-04-28T10:30:00+05:30")
    email = create_email_draft(["test@test.com"], f"Pulse [{code}]", f"<p>{code}</p>", code, code)
    doc = create_doc_append("Pre-Bookings", f"Booking: {code}", code)
    assert code in json.dumps(cal)
    assert code in json.dumps(email)
    assert code in json.dumps(doc)

def test_hitl_submit_and_reject_flow():
    """Full HITL submit → reject flow works."""
    import pillars.pillar_c_hitl.approval as approval_mod
    test_db = Path("data/hitl_queue_test_integration.db")
    original = approval_mod.DB_PATH
    approval_mod.DB_PATH = test_db
    try:
        from pillars.pillar_c_hitl.mcp_tools import create_calendar_hold
        from pillars.pillar_c_hitl.approval import submit_for_approval, reject, get_all_ops
        payload = create_calendar_hold("Test", "Desc", "2026-04-28T10:00:00+05:30", "2026-04-28T10:30:00+05:30")
        op_id = submit_for_approval(payload)
        result = reject(op_id, "duplicate", "Already booked")
        assert result["success"] is True
        ops = get_all_ops()
        assert any(o["status"] == "rejected" for o in ops)
    finally:
        approval_mod.DB_PATH = original
        if test_db.exists():
            test_db.unlink()

def test_briefing_card_has_required_fields():
    """Briefing card includes all required fields."""
    from pillars.pillar_c_hitl.briefing_card import generate_briefing_card
    pulse = {"themes": [{"theme": "Login Issues", "count": 45, "trend": {"direction": "up"}}], "quotes": ["App crashes"], "actions": ["Fix login"]}
    booking = {"booking_code": "IND-LOGN-20260428-001", "topic": "KYC/Onboarding"}
    card = generate_briefing_card(pulse, booking)
    assert card["booking_code"] == "IND-LOGN-20260428-001"
    assert "pain_points" in card
    assert "talking_points" in card
    assert len(card["talking_points"]) == 3
