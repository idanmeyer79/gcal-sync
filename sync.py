#!/usr/bin/env python3
"""
Google Calendar Sync: Source → Target

Copies all upcoming events from a source Google Calendar to a target calendar.
Each event appears with a configurable title (default: "Personal"), shown as
busy, with no notifications. Handles creates, updates, and cancellations.

Safe to run repeatedly — idempotent via a sync-state file.

Configuration is read from config.json (see config.example.json).
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timezone, timedelta

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKENS_DIR = os.path.join(SCRIPT_DIR, "tokens")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
CREDS_FILE = os.path.join(SCRIPT_DIR, "credentials.json")
STATE_FILE = os.path.join(SCRIPT_DIR, "sync_state.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "sync.log")

SOURCE_TOKEN = os.path.join(TOKENS_DIR, "token_source.json")
TARGET_TOKEN = os.path.join(TOKENS_DIR, "token_target.json")

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Bump this whenever the work-event template changes (forces re-sync of all events)
TEMPLATE_VERSION = 2

# ── Config ─────────────────────────────────────────────────────────────────────
def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            "config.json not found. Copy config.example.json to config.json "
            "and fill in your email addresses."
        )
    with open(CONFIG_FILE) as f:
        return json.load(f)

CONFIG = load_config()
SYNC_WINDOW_DAYS = CONFIG.get("sync", {}).get("sync_window_days", 90)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ── Auth helpers ───────────────────────────────────────────────────────────────
def get_service(token_path, account_label):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not os.path.exists(token_path):
        raise FileNotFoundError(
            f"Token not found for {account_label}: {token_path}\n"
            f"Run:  python3 authorize.py {account_label}"
        )

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.expired and creds.refresh_token:
        log.info(f"Refreshing token for {account_label}…")
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


# ── State helpers ──────────────────────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── Event helpers ──────────────────────────────────────────────────────────────
def event_fingerprint(event):
    """A hash of the mutable fields we care about, plus the template version."""
    key = json.dumps({
        "start": event.get("start"),
        "end": event.get("end"),
        "status": event.get("status"),
        "recurrence": event.get("recurrence"),
        "_v": TEMPLATE_VERSION,
    }, sort_keys=True)
    return hashlib.md5(key.encode()).hexdigest()


def build_target_event(source_event):
    """Create a sanitised event for the target calendar."""
    sync_cfg = CONFIG.get("sync", {})

    target_event = {
        "summary": sync_cfg.get("event_title", "Personal"),
        "start": source_event["start"],
        "end": source_event["end"],
        "status": source_event.get("status", "confirmed"),
        "transparency": "opaque" if sync_cfg.get("show_as_busy", True) else "transparent",
        "visibility": "private",
    }

    color_id = sync_cfg.get("color_id")
    if color_id:
        target_event["colorId"] = str(color_id)

    if sync_cfg.get("disable_notifications", True):
        target_event["reminders"] = {
            "useDefault": False,
            "overrides": [],
        }

    return target_event


# ── Main sync ──────────────────────────────────────────────────────────────────
def sync():
    log.info("=" * 60)
    log.info("Starting calendar sync")
    log.info(
        f"  {CONFIG['source_calendar']['email']} → "
        f"{CONFIG['target_calendar']['email']}"
    )

    source_svc = get_service(SOURCE_TOKEN, "source")
    target_svc = get_service(TARGET_TOKEN, "target")

    state = load_state()

    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=SYNC_WINDOW_DAYS)).isoformat()

    # ── Fetch all upcoming source events ──────────────────────────────────────
    log.info(f"Fetching source events ({SYNC_WINDOW_DAYS}-day window)…")
    source_events = {}
    page_token = None
    while True:
        resp = source_svc.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token,
            maxResults=500,
        ).execute()
        for e in resp.get("items", []):
            source_events[e["id"]] = e
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    log.info(f"Found {len(source_events)} source events")

    created = updated = deleted = skipped = 0

    # ── Create / update ────────────────────────────────────────────────────────
    for sid, sevent in source_events.items():
        if sevent.get("status") == "cancelled":
            continue

        target_body = build_target_event(sevent)
        fingerprint = event_fingerprint(sevent)

        if sid not in state:
            try:
                created_event = target_svc.events().insert(
                    calendarId="primary",
                    body=target_body,
                ).execute()
                state[sid] = {
                    "target_id": created_event["id"],
                    "fingerprint": fingerprint,
                }
                log.info(f"  CREATED  {sevent.get('summary', '(no title)')!r} → '{target_body['summary']}'")
                created += 1
            except Exception as exc:
                log.error(f"  ERROR creating event {sid}: {exc}")
        else:
            if state[sid]["fingerprint"] != fingerprint:
                target_id = state[sid]["target_id"]
                try:
                    target_svc.events().update(
                        calendarId="primary",
                        eventId=target_id,
                        body=target_body,
                    ).execute()
                    state[sid]["fingerprint"] = fingerprint
                    log.info(f"  UPDATED  {sevent.get('summary', '(no title)')!r}")
                    updated += 1
                except Exception as exc:
                    log.error(f"  ERROR updating event {target_id}: {exc}")
            else:
                skipped += 1

    # ── Delete target events whose source originals are gone ──────────────────
    source_ids = set(source_events.keys())
    stale_keys = [k for k in list(state.keys()) if k not in source_ids]

    for stale_key in stale_keys:
        target_id = state[stale_key]["target_id"]
        try:
            target_svc.events().delete(
                calendarId="primary",
                eventId=target_id,
            ).execute()
            del state[stale_key]
            log.info(f"  DELETED  target event {target_id} (source event removed/past)")
            deleted += 1
        except Exception as exc:
            log.warning(f"  Could not delete target event {target_id}: {exc}")
            del state[stale_key]

    save_state(state)

    log.info(
        f"Sync complete — created: {created}, updated: {updated}, "
        f"deleted: {deleted}, unchanged: {skipped}"
    )
    log.info("=" * 60)


if __name__ == "__main__":
    sync()
