#!/usr/bin/env bash
set -euo pipefail

LABEL="com.nobrokerhood.run"
DOMAIN="gui/$(id -u)"

launchctl kickstart -k "$DOMAIN/$LABEL"

echo "Kickstarted $LABEL"
echo "Check:"
echo "  tail -n 40 logs/launchd_runs.log"
echo "  ls -lt logs/runs | head"
