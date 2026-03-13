#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="gui/$(id -u)"

cd "$PROJECT_DIR"

./scripts/install_launchagent.sh --mode prewarm --times "18:58"
./scripts/install_launchagent.sh --mode hot --times "19:00"

launchctl bootout "$DOMAIN/com.predator.hack_x" 2>/dev/null || true
launchctl disable "$DOMAIN/com.predator.hack_x" 2>/dev/null || true

echo "Installed daily jobs for $PROJECT_DIR"
echo "Disabled legacy job: com.predator.hack_x"
echo "Current jobs:"
launchctl print "$DOMAIN/com.nobrokerhood.prewarm" | rg -n "state =|last exit code|runs =|path =|stdout path|stderr path"
launchctl print "$DOMAIN/com.nobrokerhood.hot" | rg -n "state =|last exit code|runs =|path =|stdout path|stderr path"
