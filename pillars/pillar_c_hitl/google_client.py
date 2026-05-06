import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import uuid as _uuid
from datetime import datetime, timezone
from core.logger import log
from core.error_logger import log_structured_error

# Lazy-import so a missing package doesn't crash on import
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import base64
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    _GOOGLE_LIBS_OK = True
except ImportError:
    _GOOGLE_LIBS_OK = False

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/documents",
]

TOKEN_PATH   = Path(__file__).parent.parent.parent / ".secrets" / "google_token.json"
CREDS_PATH   = Path(__file__).parent.parent.parent / ".secrets" / "google_credentials.json"
DOC_REGISTRY = Path(__file__).parent.parent.parent / "data" / "doc_registry.json"


# ── Demo / simulation mode ────────────────────────────────────────────────────

def _demo(op: str) -> dict:
    """Simulated success used when Google credentials are unavailable."""
    demo_id = _uuid.uuid4().hex[:8]
    base = {"success": True, "demo": True}
    if op == "calendar":
        return {**base, "event_id": f"demo-cal-{demo_id}",
                "link": "https://calendar.google.com"}
    if op == "email":
        return {**base, "draft_id": f"demo-draft-{demo_id}"}
    if op == "doc":
        return {**base, "doc_id": f"demo-doc-{demo_id}",
                "link": "https://docs.google.com"}
    return base


# ── Credential loading ────────────────────────────────────────────────────────

def get_google_creds():
    """Load/refresh credentials.
    Priority: Streamlit secrets → local .secrets/ file → None (demo mode).
    Never blocks with an interactive OAuth flow.
    """
    if not _GOOGLE_LIBS_OK:
        log.warning("google_client: google-auth libraries not installed — demo mode")
        return None

    creds = None

    # 1. Streamlit Cloud secrets (key: GOOGLE_TOKEN_JSON)
    try:
        import streamlit as st
        token_str = st.secrets.get("GOOGLE_TOKEN_JSON", "")
        if token_str:
            creds = Credentials.from_authorized_user_info(json.loads(token_str), SCOPES)
            log.info("google_client: credentials loaded from Streamlit secrets")
    except Exception:
        pass

    # 2. Local token file
    if not creds and TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        except Exception as exc:
            log.warning("google_client: could not load local token: {}", exc)

    if not creds:
        log.warning("google_client: no credentials found — demo mode")
        return None

    # Refresh if expired
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Persist refreshed token locally when writable
                try:
                    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
                    TOKEN_PATH.write_text(creds.to_json())
                except Exception:
                    pass
                log.info("google_client: token refreshed successfully")
            except Exception as exc:
                log.warning("google_client: token refresh failed: {} — demo mode", exc)
                return None
        else:
            log.warning("google_client: token invalid and no refresh_token — demo mode")
            return None

    return creds


# ── Doc ID registry (reuse the same Google Doc across bookings) ───────────────

def _get_or_create_doc(service, title: str) -> str:
    """Return the doc_id for a titled doc, creating it once and caching the ID."""
    registry = {}
    if DOC_REGISTRY.exists():
        try:
            registry = json.loads(DOC_REGISTRY.read_text())
        except Exception:
            pass

    if title in registry:
        return registry[title]

    doc    = service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]
    registry[title] = doc_id
    try:
        DOC_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        DOC_REGISTRY.write_text(json.dumps(registry, indent=2))
    except Exception:
        pass
    log.info("google_client: created Google Doc '{}' id={}", title, doc_id)
    return doc_id


# ── Executors ─────────────────────────────────────────────────────────────────

def execute_calendar_hold(payload: dict) -> dict:
    """Create a Google Calendar event. Falls back to demo mode on any failure."""
    creds = get_google_creds()
    if not creds:
        log.info("google_client: calendar_hold — demo mode")
        return _demo("calendar")
    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        event = {
            "summary":     payload["summary"],
            "description": payload["description"],
            "start":       {"dateTime": payload["start"], "timeZone": "Asia/Kolkata"},
            "end":         {"dateTime": payload["end"],   "timeZone": "Asia/Kolkata"},
            "status":      "tentative",
        }
        if payload.get("attendees"):
            event["attendees"] = [{"email": e} for e in payload["attendees"]]
        result = service.events().insert(calendarId="primary", body=event).execute()
        log.info("google_client: calendar event created id={}", result.get("id"))
        return {"success": True, "event_id": result["id"], "link": result.get("htmlLink")}
    except Exception as exc:
        log_structured_error("5-6", "google_client", "Integration", str(exc),
                             json.dumps(payload)[:200], "Event created", "Failed",
                             "Check OAuth", "Pending")
        log.warning("google_client: calendar_hold failed ({}) — demo fallback", exc)
        return _demo("calendar")


def execute_email_draft(payload: dict) -> dict:
    """Create a Gmail draft (never sends). Falls back to demo mode on any failure."""
    creds = get_google_creds()
    if not creds:
        log.info("google_client: email_draft — demo mode")
        return _demo("email")
    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        msg = MIMEMultipart("alternative")
        msg["To"]      = ", ".join(payload["to"])
        msg["Subject"] = payload["subject"]
        msg.attach(MIMEText(payload["body_plain"], "plain"))
        msg.attach(MIMEText(payload["body_html"],  "html"))
        raw   = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        draft = service.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()
        log.info("google_client: email draft created id={}", draft.get("id"))
        return {"success": True, "draft_id": draft["id"]}
    except Exception as exc:
        log_structured_error("5-6", "google_client", "Integration", str(exc),
                             json.dumps(payload)[:200], "Draft created", "Failed",
                             "Check OAuth", "Pending")
        log.warning("google_client: email_draft failed ({}) — demo fallback", exc)
        return _demo("email")


def execute_doc_append(payload: dict) -> dict:
    """Append content to a named Google Doc, reusing the same doc across calls.
    Falls back to demo mode on any failure.
    """
    creds = get_google_creds()
    if not creds:
        log.info("google_client: doc_append — demo mode")
        return _demo("doc")
    try:
        service = build("docs", "v1", credentials=creds, cache_discovery=False)
        doc_id  = _get_or_create_doc(service, payload["doc_title"])

        # Append at the true end of the document
        doc       = service.documents().get(documentId=doc_id).execute()
        end_index = doc["body"]["content"][-1]["endIndex"] - 1
        service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"insertText": {
                "location": {"index": end_index},
                "text": payload["content"] + "\n\n"
            }}]}
        ).execute()
        log.info("google_client: doc appended id={}", doc_id)
        return {"success": True, "doc_id": doc_id,
                "link": f"https://docs.google.com/document/d/{doc_id}"}
    except Exception as exc:
        log_structured_error("5-6", "google_client", "Integration", str(exc),
                             json.dumps(payload)[:200], "Doc appended", "Failed",
                             "Check OAuth", "Pending")
        log.warning("google_client: doc_append failed ({}) — demo fallback", exc)
        return _demo("doc")
