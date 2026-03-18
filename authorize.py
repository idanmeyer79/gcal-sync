#!/usr/bin/env python3
"""
Google Calendar OAuth Authorization Script
Run this ONCE for each Google account to generate a saved token.

Usage:
  python3 authorize.py source    # authorizes your source (personal) calendar
  python3 authorize.py target    # authorizes your target (work) calendar
"""

import sys
import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, "credentials.json")
TOKENS_DIR = os.path.join(SCRIPT_DIR, "tokens")

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def load_config():
    if not os.path.exists(CONFIG_FILE):
        print("\n❌  config.json not found.")
        print("    Copy config.example.json to config.json and fill in your email addresses.")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)


def main():
    config = load_config()

    account_map = {
        "source": config["source_calendar"]["email"],
        "target": config["target_calendar"]["email"],
    }
    # Also accept the user-defined labels (e.g. "personal", "work")
    account_map[config["source_calendar"]["label"]] = config["source_calendar"]["email"]
    account_map[config["target_calendar"]["label"]] = config["target_calendar"]["email"]

    if len(sys.argv) != 2 or sys.argv[1] not in account_map:
        labels = [config["source_calendar"]["label"], config["target_calendar"]["label"]]
        print(f"Usage: python3 authorize.py [source|target|{labels[0]}|{labels[1]}]")
        sys.exit(1)

    account_arg = sys.argv[1]
    email = account_map[account_arg]

    # Normalize to source/target for token filename
    if account_arg in ("source", config["source_calendar"]["label"]):
        token_key = "source"
    else:
        token_key = "target"

    token_path = os.path.join(TOKENS_DIR, f"token_{token_key}.json")

    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\n❌  credentials.json not found at: {CREDENTIALS_FILE}")
        print("    Download it from Google Cloud Console and place it in this folder.")
        sys.exit(1)

    os.makedirs(TOKENS_DIR, exist_ok=True)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        print("Missing dependencies. Run:  pip install -r requirements.txt")
        sys.exit(1)

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                print(f"\n⚠️  Token expired and could not be refreshed. Re-authorizing…")
                creds = None

        if not creds:
            print(f"\n🔐  Authorizing {email}")
            print("    A browser window will open. Sign in with the correct Google account.")
            print(f"    → Make sure you sign in as:  {email}\n")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as f:
            f.write(creds.to_json())

    print(f"\n✅  Authorization successful for {email}")
    print(f"    Token saved to: {token_path}")


if __name__ == "__main__":
    main()
