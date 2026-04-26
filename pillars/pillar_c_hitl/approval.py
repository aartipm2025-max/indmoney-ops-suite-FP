import sys
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.logger import log
from core.error_logger import log_structured_error

import sqlite3

DB_PATH = Path(__file__).parent.parent.parent / "data" / "hitl_queue.db"

REJECT_REASONS = [
    "incorrect_theme",
    "wrong_contact",
    "duplicate",
    "low_confidence",
    "other"
]

def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_ops (
            id TEXT PRIMARY KEY,
            op_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            payload_json TEXT NOT NULL,
            idempotency_key TEXT UNIQUE,
            created_at TEXT NOT NULL,
            approved_at TEXT,
            executed_at TEXT,
            retry_count INTEGER DEFAULT 0,
            last_error TEXT DEFAULT '',
            external_ids_json TEXT DEFAULT '{}',
            reject_reason TEXT,
            reject_reason_text TEXT DEFAULT '',
            request_id TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            op_id TEXT NOT NULL,
            action TEXT NOT NULL,
            details_json TEXT DEFAULT '{}',
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def submit_for_approval(tool_payload: dict, request_id: str = "") -> str:
    """Submit an MCP tool action to the HITL queue. Returns op_id.

    Idempotency key is '{request_id}:{op_type}', which guarantees:
      - No collision between different op types in the same run.
      - No crash on pipeline re-runs with the same request_id.
    If the key already exists the insert is silently skipped and the
    existing op_id is returned for full retry-safety.
    """
    op_type = tool_payload["tool"]  # e.g. "calendar_hold"
    op_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    # Key is traceable (request_id) AND unique per op_type per run
    idempotency_key = f"{request_id}:{op_type}"

    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO pending_ops "
            "(id, op_type, status, payload_json, idempotency_key, created_at, request_id) "
            "VALUES (?, ?, 'pending', ?, ?, ?, ?)",
            (op_id, op_type, json.dumps(tool_payload), idempotency_key, now, request_id)
        )
        if cursor.rowcount == 0:
            # A row with this idempotency_key already exists — skip silently
            log.warning(
                "HITL: duplicate ignored for key={}", idempotency_key
            )
            # Return the existing op_id so callers stay unaffected
            existing = conn.execute(
                "SELECT id FROM pending_ops WHERE idempotency_key=?",
                (idempotency_key,)
            ).fetchone()
            conn.close()
            return existing[0] if existing else op_id

        conn.execute(
            "INSERT INTO audit_log (op_id, action, details_json, timestamp) VALUES (?, 'submitted', ?, ?)",
            (op_id, json.dumps({"tool": op_type}), now)
        )
        conn.commit()
        log.info("HITL: submitted op_id={} type={}", op_id, op_type)
    finally:
        conn.close()
    return op_id


def approve(op_id: str) -> dict:
    """Approve a pending operation. Executes the Google API call."""
    from pillars.pillar_c_hitl.google_client import execute_calendar_hold, execute_email_draft, execute_doc_append

    conn = _get_conn()
    try:
        row = conn.execute("SELECT op_type, status, payload_json FROM pending_ops WHERE id=?", (op_id,)).fetchone()
        if not row:
            return {"success": False, "error": f"op_id {op_id} not found"}
        op_type, status, payload_json = row
        if status != "pending":
            return {"success": False, "error": f"op_id {op_id} is {status}, not pending"}

        now = datetime.now(timezone.utc).isoformat()
        conn.execute("UPDATE pending_ops SET status='approved', approved_at=? WHERE id=?", (now, op_id))
        conn.execute("INSERT INTO audit_log (op_id, action, timestamp) VALUES (?, 'approved', ?)", (op_id, now))
        conn.commit()

        # Execute the actual Google API call
        payload = json.loads(payload_json)["payload"]
        if op_type == "calendar_hold":
            result = execute_calendar_hold(payload)
        elif op_type == "email_draft":
            result = execute_email_draft(payload)
        elif op_type == "doc_append":
            result = execute_doc_append(payload)
        else:
            result = {"success": False, "error": f"Unknown op_type: {op_type}"}

        if result.get("success"):
            conn.execute("UPDATE pending_ops SET status='executed', executed_at=?, external_ids_json=? WHERE id=?",
                         (datetime.now(timezone.utc).isoformat(), json.dumps(result), op_id))
            conn.execute("INSERT INTO audit_log (op_id, action, details_json, timestamp) VALUES (?, 'executed', ?, ?)",
                         (op_id, json.dumps(result), datetime.now(timezone.utc).isoformat()))
        else:
            conn.execute("UPDATE pending_ops SET status='failed', last_error=?, retry_count=retry_count+1 WHERE id=?",
                         (result.get("error", "unknown"), op_id))
            conn.execute("INSERT INTO audit_log (op_id, action, details_json, timestamp) VALUES (?, 'failed', ?, ?)",
                         (op_id, json.dumps(result), datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return result
    finally:
        conn.close()


def reject(op_id: str, reason: str, reason_text: str = "") -> dict:
    """Reject a pending operation with a reason."""
    if reason not in REJECT_REASONS:
        return {"success": False, "error": f"Invalid reason. Must be one of: {REJECT_REASONS}"}
    conn = _get_conn()
    try:
        row = conn.execute("SELECT status FROM pending_ops WHERE id=?", (op_id,)).fetchone()
        if not row:
            return {"success": False, "error": f"op_id {op_id} not found"}
        if row[0] != "pending":
            return {"success": False, "error": f"op_id {op_id} is {row[0]}, not pending"}

        now = datetime.now(timezone.utc).isoformat()
        conn.execute("UPDATE pending_ops SET status='rejected', reject_reason=?, reject_reason_text=? WHERE id=?",
                     (reason, reason_text, op_id))
        conn.execute("INSERT INTO audit_log (op_id, action, details_json, timestamp) VALUES (?, 'rejected', ?, ?)",
                     (op_id, json.dumps({"reason": reason, "text": reason_text}), now))
        conn.commit()
        log.info("HITL: rejected op_id={} reason={}", op_id, reason)
        return {"success": True}
    finally:
        conn.close()


def get_pending_ops() -> list[dict]:
    """List all pending operations."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT id, op_type, payload_json, created_at FROM pending_ops WHERE status='pending' ORDER BY created_at").fetchall()
        return [{"id": r[0], "op_type": r[1], "payload": json.loads(r[2]), "created_at": r[3]} for r in rows]
    finally:
        conn.close()


def get_all_ops() -> list[dict]:
    """List all operations with status."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT id, op_type, status, created_at, approved_at, executed_at, reject_reason, external_ids_json FROM pending_ops ORDER BY created_at DESC").fetchall()
        return [{"id": r[0], "op_type": r[1], "status": r[2], "created_at": r[3], "approved_at": r[4], "executed_at": r[5], "reject_reason": r[6], "external_ids": json.loads(r[7] or "{}")} for r in rows]
    finally:
        conn.close()
