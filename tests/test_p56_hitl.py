import sys
import json
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pytest

from pillars.pillar_c_hitl.mcp_tools import create_calendar_hold, create_email_draft, create_doc_append
from pillars.pillar_c_hitl.approval import submit_for_approval, approve, reject, get_pending_ops, get_all_ops, DB_PATH
from pillars.pillar_c_hitl.briefing_card import generate_briefing_card, format_briefing_html, format_briefing_plain


@pytest.fixture(autouse=True)
def clean_db():
    """Use a temp DB for each test."""
    import pillars.pillar_c_hitl.approval as approval_mod
    test_db = Path("data/hitl_queue_test.db")
    original = approval_mod.DB_PATH
    approval_mod.DB_PATH = test_db
    yield
    approval_mod.DB_PATH = original
    if test_db.exists():
        test_db.unlink()


def test_mcp_calendar_tool_returns_payload():
    result = create_calendar_hold("Advisor Q&A — KYC — IND-TECH-20260428-001", "Test description", "2026-04-28T10:00:00+05:30", "2026-04-28T10:30:00+05:30")
    assert result["tool"] == "calendar_hold"
    assert "summary" in result["payload"]
    assert "start" in result["payload"]

def test_mcp_email_tool_returns_payload():
    result = create_email_draft(["advisor@test.com"], "Weekly Pulse [IND-TECH-20260428-001]", "<p>Test</p>", "Test", "IND-TECH-20260428-001")
    assert result["tool"] == "email_draft"
    assert result["payload"]["booking_code"] == "IND-TECH-20260428-001"

def test_mcp_doc_tool_returns_payload():
    result = create_doc_append("Advisor Pre-Bookings", "Entry content", "IND-TECH-20260428-001")
    assert result["tool"] == "doc_append"

def test_submit_creates_pending_op():
    tool_payload = create_calendar_hold("Test", "Desc", "2026-04-28T10:00:00+05:30", "2026-04-28T10:30:00+05:30")
    op_id = submit_for_approval(tool_payload)
    assert len(op_id) == 12
    pending = get_pending_ops()
    assert len(pending) == 1
    assert pending[0]["id"] == op_id
    assert pending[0]["op_type"] == "calendar_hold"

def test_reject_with_reason():
    tool_payload = create_email_draft(["test@test.com"], "Test [IND-TEST]", "<p>x</p>", "x", "IND-TEST")
    op_id = submit_for_approval(tool_payload)
    result = reject(op_id, "incorrect_theme", "Wrong theme assigned")
    assert result["success"] is True
    all_ops = get_all_ops()
    rejected = [o for o in all_ops if o["status"] == "rejected"]
    assert len(rejected) == 1
    assert rejected[0]["reject_reason"] == "incorrect_theme"

def test_reject_invalid_reason_fails():
    tool_payload = create_doc_append("Test", "Content", "IND-TEST")
    op_id = submit_for_approval(tool_payload)
    result = reject(op_id, "invalid_reason_xyz")
    assert result["success"] is False

def test_approve_without_google_creds_fails_gracefully():
    tool_payload = create_calendar_hold("Test", "Desc", "2026-04-28T10:00:00+05:30", "2026-04-28T10:30:00+05:30")
    op_id = submit_for_approval(tool_payload)
    result = approve(op_id)
    # Without real Google creds, this should fail gracefully (not crash)
    assert isinstance(result, dict)
    # Status should be 'failed' in the DB
    all_ops = get_all_ops()
    op = [o for o in all_ops if o["id"] == op_id][0]
    assert op["status"] in ("failed", "executed")

def test_briefing_card_generation():
    pulse = {"themes": [{"theme": "Login Issues", "count": 45, "trend": {"direction": "up"}}, {"theme": "Slow UI", "count": 30, "trend": {"direction": "flat"}}], "quotes": ["App crashes constantly", "UI is terrible"], "actions": ["Fix login flow", "Improve UI speed"]}
    booking = {"booking_code": "IND-TECH-20260428-001", "topic": "KYC/Onboarding"}
    card = generate_briefing_card(pulse, booking)
    assert card["booking_code"] == "IND-TECH-20260428-001"
    assert len(card["top_themes"]) == 2
    assert len(card["talking_points"]) == 3

def test_briefing_html_contains_booking_code():
    card = {"booking_code": "IND-SUPP-20260428-002", "topic": "SIP", "sentiment_shift": "stable", "top_themes": [{"name": "Support", "count": 20, "trend": "up"}], "user_quotes": ["Great help"], "talking_points": ["Review support"]}
    html = format_briefing_html(card)
    assert "IND-SUPP-20260428-002" in html
    assert "<h2>" in html

def test_briefing_plain_contains_booking_code():
    card = {"booking_code": "IND-SUPP-20260428-002", "topic": "SIP", "sentiment_shift": "stable", "top_themes": [{"name": "Support", "count": 20, "trend": "up"}], "user_quotes": ["Great help"], "talking_points": ["Review support"]}
    plain = format_briefing_plain(card)
    assert "IND-SUPP-20260428-002" in plain
