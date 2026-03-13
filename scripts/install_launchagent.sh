#!/usr/bin/env bash
set -euo pipefail

LABEL="com.nobrokerhood.run"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
AGENT_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$AGENT_DIR/$LABEL.plist"
WRAPPER_PATH="$AGENT_DIR/${LABEL}.wrapper.sh"
RUNS_LOG="$PROJECT_DIR/logs/launchd_runs.log"
ERR_LOG="$PROJECT_DIR/logs/launchd_errors.log"
DOMAIN="gui/$(id -u)"

usage() {
  cat <<USAGE
Usage:
  $0 --times "HH:MM,HH:MM,..."

Notes:
- macOS may block launchd from reading scripts on Desktop.
- If your project is under Desktop and job exits with code 126, move the repo to a non-protected path like:
  /Users/$USER/nobrokerhood
USAGE
}

if [[ $# -ne 2 || "$1" != "--times" ]]; then
  usage
  exit 1
fi

TIMES_CSV="$2"
IFS=',' read -r -a TIMES <<< "$TIMES_CSV"
if [[ ${#TIMES[@]} -eq 0 ]]; then
  echo "Invalid --times value: $TIMES_CSV"
  exit 1
fi

mkdir -p "$AGENT_DIR" "$PROJECT_DIR/logs"

build_calendar_intervals() {
  local entries=()
  local t hh mm
  for t in "${TIMES[@]}"; do
    t="${t//[[:space:]]/}"
    if [[ ! "$t" =~ ^([01][0-9]|2[0-3]):([0-5][0-9])$ ]]; then
      echo "Invalid time '$t'. Expected HH:MM (24-hour)."
      exit 1
    fi
    hh="${t%%:*}"
    mm="${t##*:}"
    entries+=(
"        <dict>"
"            <key>Hour</key>"
"            <integer>$((10#$hh))</integer>"
"            <key>Minute</key>"
"            <integer>$((10#$mm))</integer>"
"        </dict>"
    )
  done
  printf '%s\n' "${entries[@]}"
}

CALENDAR_XML="$(build_calendar_intervals)"

cat > "$WRAPPER_PATH" <<WRAP
#!/usr/bin/env bash
set -euo pipefail
cd "$PROJECT_DIR"
exec /usr/bin/caffeinate -i "$PROJECT_DIR/run.sh"
WRAP
chmod +x "$WRAPPER_PATH"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>$WRAPPER_PATH</string>
    </array>

    <key>RunAtLoad</key>
    <false/>

    <key>StartCalendarInterval</key>
    <array>
$CALENDAR_XML
    </array>

    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>

    <key>StandardOutPath</key>
    <string>$RUNS_LOG</string>

    <key>StandardErrorPath</key>
    <string>$ERR_LOG</string>
</dict>
</plist>
PLIST

plutil -lint "$PLIST_PATH" >/dev/null

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST_PATH"
launchctl enable "$DOMAIN/$LABEL"

launchctl print "$DOMAIN/$LABEL" | rg -n "state =|last exit code|runs =|path =|program =" -i

echo "Installed and loaded: $PLIST_PATH"
echo "Wrapper: $WRAPPER_PATH"
echo "Times: $TIMES_CSV"
echo "Manual trigger: launchctl kickstart -k \"$DOMAIN/$LABEL\""
