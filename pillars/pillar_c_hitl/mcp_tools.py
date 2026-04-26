import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.logger import log

# Tool 1: Calendar Hold
def create_calendar_hold(
    summary: str,      # e.g. "Advisor Q&A — KYC/Onboarding — IND-TECH-20260428-001"
    description: str,   # includes booking code + topic + advisor briefing
    start_iso: str,     # ISO8601 with timezone
    end_iso: str,       # ISO8601 with timezone
    attendees: list[str] = None  # email list (optional)
) -> dict:
    """Returns a structured payload for the HITL queue. Does NOT execute."""
    return {
        "tool": "calendar_hold",
        "payload": {
            "summary": summary,
            "description": description,
            "start": start_iso,
            "end": end_iso,
            "attendees": attendees or []
        }
    }

# Tool 2: Email Draft
def create_email_draft(
    to: list[str],
    subject: str,       # must contain [IND-{booking_code}]
    body_html: str,
    body_plain: str,
    booking_code: str
) -> dict:
    """Returns a structured payload for the HITL queue. Does NOT execute."""
    return {
        "tool": "email_draft",
        "payload": {
            "to": to,
            "subject": subject,
            "body_html": body_html,
            "body_plain": body_plain,
            "booking_code": booking_code
        }
    }

# Tool 3: Notes/Doc Append
def create_doc_append(
    doc_title: str,     # e.g. "Advisor Pre-Bookings"
    content: str,       # structured text to append
    booking_code: str
) -> dict:
    """Returns a structured payload for the HITL queue. Does NOT execute."""
    return {
        "tool": "doc_append",
        "payload": {
            "doc_title": doc_title,
            "content": content,
            "booking_code": booking_code
        }
    }
