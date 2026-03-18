#!/bin/bash
# Installs a macOS launchd job to run the sync automatically every hour.
# Usage: bash install-schedule.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_TEMPLATE="$SCRIPT_DIR/com.gcal-sync.plist.template"
PLIST_NAME="com.gcal-sync.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
GUI_TARGET="gui/$(id -u)"

echo "Installing gcal-sync schedule…"

# Generate plist from template with the actual install path
sed "s|__INSTALL_DIR__|$SCRIPT_DIR|g" "$PLIST_TEMPLATE" > "$PLIST_DEST"

# Unload existing job if already running (ignore errors if not loaded)
launchctl bootout "$GUI_TARGET/com.gcal-sync" 2>/dev/null || true

launchctl bootstrap "$GUI_TARGET" "$PLIST_DEST"

echo ""
echo "✅  Done! The sync will run automatically every hour."
echo ""
echo "Test now:         launchctl start com.gcal-sync"
echo "Check logs:       tail -5 $SCRIPT_DIR/sync.log"
echo "Uninstall:        bash $SCRIPT_DIR/uninstall-schedule.sh"
