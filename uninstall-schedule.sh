#!/bin/bash
# Removes the gcal-sync launchd job.

PLIST_NAME="com.gcal-sync.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
GUI_TARGET="gui/$(id -u)"

launchctl bootout "$GUI_TARGET/com.gcal-sync" 2>/dev/null || true
rm -f "$PLIST_DEST"

echo "✅  gcal-sync schedule removed."
