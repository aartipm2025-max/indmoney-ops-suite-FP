"""
Re-run the Google OAuth flow to obtain a fresh token.
Run once from the terminal:
    .venv\Scripts\python.exe scripts\reauth_google.py
A browser window will open. Sign in, grant permissions, then close.
The new token is saved to .secrets/google_token.json automatically.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/documents",
]

CREDS_PATH = Path(__file__).parent.parent / ".secrets" / "google_credentials.json"
TOKEN_PATH  = Path(__file__).parent.parent / ".secrets" / "google_token.json"

if not CREDS_PATH.exists():
    print(f"[FAIL] Cannot find credentials file at: {CREDS_PATH}")
    print("  Download it from Google Cloud Console → APIs & Services → Credentials")
    sys.exit(1)

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("[FAIL] google-auth-oauthlib not installed.")
    print("  Run: .venv\\Scripts\\pip install google-auth-oauthlib")
    sys.exit(1)

print("[INFO] Starting OAuth flow — your browser will open...")
print(f"[INFO] Using credentials from: {CREDS_PATH}")

flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)

# run_local_server opens a browser and listens on localhost for the callback
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

# Save to token file
TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
TOKEN_PATH.write_text(creds.to_json())

print(f"\n[OK] New token saved to: {TOKEN_PATH}")
print(f"     valid={creds.valid}, has refresh_token={bool(creds.refresh_token)}")
print("\n[DONE] Re-authentication complete. Email draft & Calendar hold should now work.")
