#!/usr/bin/env bash
set -euo pipefail

LABEL="com.nobrokerhood.run"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_PATH="$PROJECT_DIR/launchd/$LABEL.plist"
DOMAIN="gui/$(id -u)"

if [[ ! -f "$PLIST_PATH" ]]; then
  echo "Missing plist: $PLIST_PATH"
  echo "Generate it first: ./scripts/setup_launchd.sh --times \"HH:MM,...\""
  exit 1
fi

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST_PATH"
launchctl enable "$DOMAIN/$LABEL"
launchctl print "$DOMAIN/$LABEL" | rg -n "state =|last exit code|runs =|path =|Program"

echo "Loaded $LABEL"
