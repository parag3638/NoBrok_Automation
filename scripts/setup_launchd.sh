#!/usr/bin/env bash
set -euo pipefail

LABEL="com.nobrokerhood.run"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_DIR="$PROJECT_DIR/launchd"
PLIST_PATH="$PLIST_DIR/$LABEL.plist"
WRAPPER_PATH="$PROJECT_DIR/scripts/launchd_caffeinate_wrapper.sh"
LOG_DIR="$PROJECT_DIR/logs"
RUNS_LOG="$LOG_DIR/launchd_runs.log"
ERR_LOG="$LOG_DIR/launchd_errors.log"

usage() {
  cat <<USAGE
Usage:
  $0 --times "HH:MM,HH:MM,..."

Examples:
  $0 --times "21:58"
  $0 --times "21:58,22:00,22:02"

Then load with:
  launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
  launchctl enable "gui/$(id -u)/$LABEL"
USAGE
}

if [[ $# -ne 2 || "$1" != "--times" ]]; then
  usage
  exit 1
fi

TIMES_CSV="$2"
if [[ -z "$TIMES_CSV" ]]; then
  echo "No run times supplied."
  exit 1
fi

mkdir -p "$PLIST_DIR" "$LOG_DIR"

IFS=',' read -r -a TIMES <<< "$TIMES_CSV"
if [[ ${#TIMES[@]} -eq 0 ]]; then
  echo "Invalid --times value: $TIMES_CSV"
  exit 1
fi

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
echo "Created: $PLIST_PATH"
echo "Times: $TIMES_CSV"
echo "Next steps:"
echo "  launchctl bootout \"gui/$(id -u)/$LABEL\" 2>/dev/null || true"
echo "  launchctl bootstrap \"gui/$(id -u)\" \"$PLIST_PATH\""
echo "  launchctl enable \"gui/$(id -u)/$LABEL\""
echo "  launchctl print \"gui/$(id -u)/$LABEL\" | rg 'last exit code|state|next scheduled run'"
