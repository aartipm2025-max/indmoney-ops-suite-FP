"""Diagnostic: test Google OAuth credential loading and refresh."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Step 1: Check google libs
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    print("[OK] google-auth libraries found")
except ImportError as e:
    print(f"[FAIL] google-auth missing: {e}")
    sys.exit(1)

TOKEN_PATH = Path(__file__).parent.parent / ".secrets" / "google_token.json"

# Step 2: Load token file
try:
    token_data = json.loads(TOKEN_PATH.read_text())
    print(f"[OK] Token loaded. Expiry: {token_data.get('expiry')}")
    print(f"     Has refresh_token: {bool(token_data.get('refresh_token'))}")
    print(f"     client_id present: {bool(token_data.get('client_id'))}")
    print(f"     client_secret present: {bool(token_data.get('client_secret'))}")
except Exception as e:
    print(f"[FAIL] Cannot read token file: {e}")
    sys.exit(1)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/documents",
]

# Step 3: Load creds
try:
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    print(f"[OK] Credentials object created. valid={creds.valid}, expired={creds.expired}")
except Exception as e:
    print(f"[FAIL] Could not create Credentials object: {e}")
    sys.exit(1)

# Step 4: Try refresh if needed
if creds.valid:
    print("[OK] Credentials are already valid — no refresh needed.")
else:
    print("[INFO] Token is NOT valid — attempting refresh...")
    if not creds.expired:
        print("[WARN] Token is not expired but still invalid — unusual state.")
    if not creds.refresh_token:
        print("[FAIL] No refresh_token present — re-run OAuth flow needed.")
        sys.exit(1)
    try:
        creds.refresh(Request())
        print(f"[OK] Token refreshed successfully! valid={creds.valid}")
        TOKEN_PATH.write_text(creds.to_json())
        print("[OK] Updated token saved to .secrets/google_token.json")
    except Exception as e:
        print(f"[FAIL] Token refresh error: {e}")
        sys.exit(1)

print("\n[RESULT] Google credentials are operational.")
