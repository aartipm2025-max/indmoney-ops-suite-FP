"""Live smoke-test: email draft + calendar hold using real Google APIs."""
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from pillars.pillar_c_hitl.google_client import execute_email_draft, execute_calendar_hold

# ── Email Draft ───────────────────────────────────────────────────────────────
print("=" * 55)
print("TEST 1: Email Draft")
print("=" * 55)
email_payload = {
    "to": ["test@example.com"],
    "subject": "[SMOKE TEST] INDmoney Ops Suite — Draft Check",
    "body_plain": "This is a live smoke-test draft. Safe to delete.",
    "body_html": "<p>This is a <b>live smoke-test</b> draft. Safe to delete.</p>",
}
result = execute_email_draft(email_payload)
print(f"Result : {result}")
if result.get("success") and not result.get("demo"):
    print("[PASS] Real Gmail draft created ✓")
elif result.get("demo"):
    print("[WARN] Fell back to demo mode — check credentials")
else:
    print("[FAIL] Email draft failed")

# ── Calendar Hold ─────────────────────────────────────────────────────────────
print()
print("=" * 55)
print("TEST 2: Calendar Hold")
print("=" * 55)
now   = datetime.now(timezone.utc)
start = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
end   = start + timedelta(hours=1)

cal_payload = {
    "summary":     "[SMOKE TEST] INDmoney Ops Suite — Calendar Hold",
    "description": "Auto-created by smoke test. Safe to delete.",
    "start":       start.isoformat(),
    "end":         end.isoformat(),
    "attendees":   [],
}
result = execute_calendar_hold(cal_payload)
print(f"Result : {result}")
if result.get("success") and not result.get("demo"):
    print(f"[PASS] Real Calendar event created ✓  link={result.get('link')}")
elif result.get("demo"):
    print("[WARN] Fell back to demo mode — check credentials")
else:
    print("[FAIL] Calendar hold failed")

print()
print("Smoke test complete.")
