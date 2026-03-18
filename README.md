# gcal-sync

A lightweight Python tool that one-way syncs events from one Google Calendar to another. Events appear on the target calendar with a neutral title (e.g. "Personal"), shown as busy, with no notifications — so your coworkers see you're unavailable without seeing the details.

**Features:**

- One-way sync: source calendar → target calendar
- Events appear with a configurable title (default: "Personal")
- Shown as busy with no notifications on the target calendar
- Configurable event color
- Handles new events, updates, and cancellations
- Runs automatically every hour via macOS launchd (or cron)
- Safe to run repeatedly (idempotent)

## Setup

### 1. Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **Select a project** → **New Project**
3. Name it anything (e.g. `gcal-sync`) → **Create**

### 2. Enable the Google Calendar API

1. In the left menu, go to **APIs & Services → Library**
2. Search for **Google Calendar API** → click it → **Enable**

### 3. Configure the OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Choose **External** → **Create**
3. Fill in an app name, your email for support and developer contact
4. Click **Save and Continue** through all steps
5. Click **Publish App** → **Confirm** (this prevents tokens from expiring after 7 days)

### 4. Create OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Click **Create**, then **Download JSON**
5. Rename the file to `credentials.json` and move it into this folder

### 5. Configure

Copy the example config and fill in your email addresses:

```bash
cp config.example.json config.json
```

Edit `config.json`:

```json
{
  "source_calendar": {
    "label": "personal",
    "email": "you@gmail.com"
  },
  "target_calendar": {
    "label": "work",
    "email": "you@company.com"
  },
  "sync": {
    "event_title": "Personal",
    "color_id": "5",
    "show_as_busy": true,
    "disable_notifications": true,
    "sync_window_days": 90
  }
}
```

**Color IDs:** 1 = Lavender, 2 = Sage, 3 = Grape, 4 = Flamingo, 5 = Banana (yellow), 6 = Tangerine, 7 = Peacock, 8 = Graphite, 9 = Blueberry, 10 = Basil, 11 = Tomato

### 6. Install Dependencies

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 7. Authorize Both Accounts

Each command opens a browser — sign in with the correct Google account.

```bash
venv/bin/python3 authorize.py source
venv/bin/python3 authorize.py target
```

### 8. Test It

```bash
venv/bin/python3 sync.py
```

You should see output like:

```
Found 12 source events
  CREATED  'Dentist' → 'Personal'
  CREATED  'Gym' → 'Personal'
Sync complete — created: 2, updated: 0, deleted: 0, unchanged: 10
```

### 9. Automate (macOS)

Install a launchd job that runs the sync every hour:

```bash
chmod +x run-sync.sh install-schedule.sh
bash install-schedule.sh
```

Test the scheduled job:

```bash
launchctl start com.gcal-sync
```

Check logs:

```bash
tail -5 sync.log
```

To uninstall the schedule:

```bash
bash uninstall-schedule.sh
```

> **Important:** Install the project in a location outside `~/Documents`, `~/Desktop`, or `~/Downloads` — macOS blocks background processes from accessing those folders. `~/.gcal-sync` works well.

#### Alternative: cron

If you prefer cron over launchd, add this to your crontab (`crontab -e`):

```
0 * * * * /path/to/gcal-sync/run-sync.sh >> /path/to/gcal-sync/cron.log 2>&1
```

## Troubleshooting

**Token expired or revoked:** Delete the stale token and re-authorize:

```bash
rm tokens/token_source.json
venv/bin/python3 authorize.py source
```

**"Operation not permitted" from launchd:** The project folder is in a macOS-protected directory. Move it to `~/.gcal-sync` or another location outside `~/Documents`, `~/Desktop`, or `~/Downloads`.

**Sync runs manually but not via launchd:** Check `launchd_stderr.log` in the project folder for errors.

## Files

| File | Purpose |
|------|---------|
| `config.example.json` | Template config — copy to `config.json` |
| `config.json` | Your config (git-ignored) |
| `credentials.json` | Google OAuth credentials (git-ignored) |
| `authorize.py` | One-time auth script |
| `sync.py` | The sync engine |
| `run-sync.sh` | Shell wrapper for launchd/cron |
| `install-schedule.sh` | Installs the macOS launchd job |
| `uninstall-schedule.sh` | Removes the launchd job |
| `com.gcal-sync.plist.template` | launchd plist template |
| `requirements.txt` | Python dependencies |
| `tokens/` | Saved auth tokens (git-ignored, auto-created) |
| `sync_state.json` | Tracks synced events (git-ignored, auto-created) |
| `sync.log` | Log file (git-ignored, auto-created) |

## License

MIT
