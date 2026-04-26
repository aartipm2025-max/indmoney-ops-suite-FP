# Safety Rules & Guardrails — Pillar C HITL Layer

## Core Rules

1. **No auto-send.** Gmail actions create drafts only. The `execute_email_draft()` function calls `drafts().create()`, never `messages().send()`. Auto-sending is permanently forbidden.

2. **No PII in MCP payloads.** Email addresses in `to` fields are the only permitted identifier. No Aadhaar, PAN, phone numbers, or account numbers may appear in any payload field stored in the HITL queue.

3. **Human approval required.** Every MCP tool action must pass through `submit_for_approval()` and receive an explicit `approve()` call before any Google API executes. Automated approval is forbidden.

4. **Reject-with-reason mandatory.** Every rejection must specify a reason from the `REJECT_REASONS` enum (`incorrect_theme`, `wrong_contact`, `duplicate`, `low_confidence`, `other`) plus optional free-text. All rejections are written to the `audit_log` table.

5. **Booking code in all three outputs.** The booking code must appear in the calendar event description, the email subject and body, and the Google Doc content. Actions missing a booking code must be rejected.

6. **IST timezone.** All time references in calendar events and email bodies must state timezone explicitly as `Asia/Kolkata` (IST, UTC+5:30).

7. **Audit trail immutable.** The `audit_log` table is append-only. No row may be deleted or updated after insert.
