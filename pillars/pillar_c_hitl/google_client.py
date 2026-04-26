import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
from datetime import datetime, timezone
from core.logger import log
from core.error_logger import log_structured_error

# Google API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/documents",
]

TOKEN_PATH = Path(__file__).parent.parent.parent / ".secrets" / "google_token.json"
CREDS_PATH = Path(__file__).parent.parent.parent / ".secrets" / "google_credentials.json"


def get_google_creds() -> Credentials:
    """Load or refresh Google OAuth credentials."""
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                log.warning("google_client: no credentials file at {}", CREDS_PATH)
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=8765)
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json())
        log.info("google_client: credentials saved to {}", TOKEN_PATH)
    return creds


def execute_calendar_hold(payload: dict) -> dict:
    """Create a real Google Calendar event."""
    try:
        creds = get_google_creds()
        if not creds:
            return {"success": False, "error": "No Google credentials"}
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        event = {
            "summary": payload["summary"],
            "description": payload["description"],
            "start": {"dateTime": payload["start"], "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": payload["end"], "timeZone": "Asia/Kolkata"},
            "status": "tentative",
        }
        if payload.get("attendees"):
            event["attendees"] = [{"email": e} for e in payload["attendees"]]
        result = service.events().insert(calendarId="primary", body=event).execute()
        log.info("google_client: calendar event created: {}", result.get("id"))
        return {"success": True, "event_id": result["id"], "link": result.get("htmlLink")}
    except Exception as exc:
        log_structured_error("5-6", "google_client", "Integration", str(exc), json.dumps(payload)[:200], "Event created", "Failed", "Check OAuth", "Pending")
        return {"success": False, "error": str(exc)}


def execute_email_draft(payload: dict) -> dict:
    """Create a real Gmail draft (never sends)."""
    try:
        creds = get_google_creds()
        if not creds:
            return {"success": False, "error": "No Google credentials"}
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        msg = MIMEMultipart("alternative")
        msg["To"] = ", ".join(payload["to"])
        msg["Subject"] = payload["subject"]
        msg.attach(MIMEText(payload["body_plain"], "plain"))
        msg.attach(MIMEText(payload["body_html"], "html"))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        log.info("google_client: email draft created: {}", draft.get("id"))
        return {"success": True, "draft_id": draft["id"]}
    except Exception as exc:
        log_structured_error("5-6", "google_client", "Integration", str(exc), json.dumps(payload)[:200], "Draft created", "Failed", "Check OAuth", "Pending")
        return {"success": False, "error": str(exc)}


def execute_doc_append(payload: dict) -> dict:
    """Append content to a Google Doc."""
    try:
        creds = get_google_creds()
        if not creds:
            return {"success": False, "error": "No Google credentials"}
        service = build("docs", "v1", credentials=creds, cache_discovery=False)
        # For demo: create a new doc if none exists, or append to existing
        # Simple approach: create a doc with the booking code as title
        doc = service.documents().create(body={"title": payload["doc_title"]}).execute()
        doc_id = doc["documentId"]
        # Append content
        requests_body = [{"insertText": {"location": {"index": 1}, "text": payload["content"] + "\n\n"}}]
        service.documents().batchUpdate(documentId=doc_id, body={"requests": requests_body}).execute()
        log.info("google_client: doc created/appended: {}", doc_id)
        return {"success": True, "doc_id": doc_id, "link": f"https://docs.google.com/document/d/{doc_id}"}
    except Exception as exc:
        log_structured_error("5-6", "google_client", "Integration", str(exc), json.dumps(payload)[:200], "Doc appended", "Failed", "Check OAuth", "Pending")
        return {"success": False, "error": str(exc)}
