#!/bin/bash
# Wrapper script for launchd / cron — ensures correct environment for the venv Python
SCRIPT_DIR="$(dirname "$0")"
exec "$SCRIPT_DIR/venv/bin/python3" "$SCRIPT_DIR/sync.py"
