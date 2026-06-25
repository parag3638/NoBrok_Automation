#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
RUN_LOG_DIR="$LOG_DIR/runs"
APPIUM_LOG_DIR="$LOG_DIR/appium"
EMULATOR_LOG_DIR="$LOG_DIR/emulator"
SCREENSHOT_DIR="$PROJECT_DIR/screenshots"
LOCK_FILE="$PROJECT_DIR/.run.lock"
RUN_TS="$(date +"%Y%m%d_%H%M%S")"
RUN_LOG="$RUN_LOG_DIR/run_$RUN_TS.log"
SCRIPT_START_EPOCH="$(date +%s)"
MODE="${1:-race}"
TEE_DIR=""
TEE_FIFO=""
TEE_PID=""
DEVICE_STAGE_START_EPOCH=""
PYTHON_STAGE_START_EPOCH=""

# Runtime knobs (override via env if needed)
: "${AVD_NAME:=Pixel_7}"
: "${APPIUM_HOST:=127.0.0.1}"
: "${APPIUM_PORT:=4723}"
: "${EMULATOR_BOOT_TIMEOUT_SEC:=240}"
: "${APPIUM_START_TIMEOUT_SEC:=60}"
: "${POST_EMULATOR_BOOT_STABILIZE_SEC:=5}"
: "${POST_APPIUM_START_STABILIZE_SEC:=5}"
: "${ADB_CMD_TIMEOUT_SEC:=12}"
: "${ADB_STABLE_TIMEOUT_SEC:=45}"
: "${ADB_STABLE_SUCCESS_COUNT:=3}"
: "${EMULATOR_HEADLESS:=}"
: "${WRAPPER_PREP_CUTOFF_SEC:=}"

mkdir -p \
  "$LOG_DIR" \
  "$RUN_LOG_DIR" \
  "$APPIUM_LOG_DIR" \
  "$EMULATOR_LOG_DIR" \
  "$SCREENSHOT_DIR/success" \
  "$SCREENSHOT_DIR/failure"

# Send this wrapper's output to both terminal and run log without leaving
# a background process-substitution writer racing the shell prompt on exit.
exec 3>&1 4>&2
TEE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/nobrok_run.XXXXXX")"
TEE_FIFO="$TEE_DIR/run.pipe"
mkfifo "$TEE_FIFO"
tee -a "$RUN_LOG" < "$TEE_FIFO" >&3 &
TEE_PID=$!
exec > "$TEE_FIFO" 2>&1

echo "[$(date +"%F %T")] Run started"
echo "[$(date +"%F %T")] Run log: $RUN_LOG"
echo "[$(date +"%F %T")] Mode: $MODE"

cleanup() {
  local exit_code=$?
  SCRIPT_END_EPOCH="$(date +%s)"
  SCRIPT_ELAPSED_SEC=$((SCRIPT_END_EPOCH - SCRIPT_START_EPOCH))
  SCRIPT_ELAPSED_FMT="$(printf '%02d:%02d:%02d' $((SCRIPT_ELAPSED_SEC/3600)) $(((SCRIPT_ELAPSED_SEC%3600)/60)) $((SCRIPT_ELAPSED_SEC%60)))"

  if [[ -n "${EMULATOR_SERIAL:-}" ]]; then
    echo "[$(date +"%F %T")] Shutting down emulator: $EMULATOR_SERIAL"
    adb -s "$EMULATOR_SERIAL" emu kill >/dev/null 2>&1 || true
  fi

  APP_PID_ON_PORT="$(lsof -nP -iTCP:"$APPIUM_PORT" -sTCP:LISTEN -t 2>/dev/null | head -n 1 || true)"
  if [[ -n "${APP_PID_ON_PORT:-}" ]]; then
    APP_CMDLINE="$(ps -p "$APP_PID_ON_PORT" -o command= 2>/dev/null || true)"
    if [[ "$APP_CMDLINE" == *appium* ]]; then
      echo "[$(date +"%F %T")] Shutting down Appium: pid=$APP_PID_ON_PORT"
      kill "$APP_PID_ON_PORT" >/dev/null 2>&1 || true
      sleep 1
      if ps -p "$APP_PID_ON_PORT" >/dev/null 2>&1; then
        kill -9 "$APP_PID_ON_PORT" >/dev/null 2>&1 || true
      fi
    fi
  fi

  rm -f "$LOCK_FILE"
  echo "[$(date +"%F %T")] Total run time: ${SCRIPT_ELAPSED_SEC}s (${SCRIPT_ELAPSED_FMT})"
  # Guarded: cleanup may fire before append_automation_log is defined on an early error.
  if declare -F append_automation_log >/dev/null 2>&1; then
    append_automation_log "run_total" "success" "elapsed_sec=${SCRIPT_ELAPSED_SEC} fmt=${SCRIPT_ELAPSED_FMT} exit_code=${exit_code}"
  fi
  echo "[$(date +"%F %T")] Lock removed"

  exec 1>&3 2>&4
  if [[ -n "${TEE_PID:-}" ]]; then
    wait "$TEE_PID" 2>/dev/null || true
  fi
  exec 3>&- 4>&-
  if [[ -n "${TEE_FIFO:-}" ]]; then
    rm -f "$TEE_FIFO"
  fi
  if [[ -n "${TEE_DIR:-}" ]]; then
    rmdir "$TEE_DIR" 2>/dev/null || true
  fi
  return "$exit_code"
}

if [[ -f "$LOCK_FILE" ]]; then
  LOCK_PID="$(cat "$LOCK_FILE" 2>/dev/null || true)"
  if [[ -n "${LOCK_PID:-}" ]] && ps -p "$LOCK_PID" >/dev/null 2>&1; then
    echo "[$(date +"%F %T")] Another run is active (pid=$LOCK_PID, lock: $LOCK_FILE). Exiting."
    exit 0
  fi
  echo "[$(date +"%F %T")] Stale lock detected (pid=${LOCK_PID:-unknown}). Removing: $LOCK_FILE"
  rm -f "$LOCK_FILE"
fi

echo "$$" > "$LOCK_FILE"
trap cleanup EXIT

echo "[$(date +"%F %T")] Lock acquired"

# 1) Export Android/Appium related vars.
if [[ -z "${ANDROID_HOME:-}" ]]; then
  if [[ -d "$HOME/Library/Android/sdk" ]]; then
    export ANDROID_HOME="$HOME/Library/Android/sdk"
  elif [[ -d "$HOME/Android/Sdk" ]]; then
    export ANDROID_HOME="$HOME/Android/Sdk"
  fi
fi

if [[ -n "${ANDROID_HOME:-}" ]]; then
  export ANDROID_SDK_ROOT="$ANDROID_HOME"
  export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
fi

# Include common Homebrew/global bins for appium/node tools.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "[$(date +"%F %T")] ANDROID_HOME=${ANDROID_HOME:-unset}"

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[$(date +"%F %T")] Missing command: $cmd"
    exit 1
  fi
}

format_elapsed() {
  local total_sec="$1"
  printf '%02d:%02d:%02d' $((total_sec/3600)) $(((total_sec%3600)/60)) $((total_sec%60))
}

append_automation_log() {
  local step="$1"
  local status="$2"
  local details="$3"
  printf '%s | step=%s | status=%s | slot=- | details=%s\n' \
    "$(date +"%F %T")" \
    "$step" \
    "$status" \
    "$details" >> "$LOG_DIR/automation.log"
}

require_cmd python3
require_cmd adb
require_cmd emulator
require_cmd curl
require_cmd appium
require_cmd lsof

load_config_value() {
  local attr="$1"
  python3 - "$attr" <<'PY'
import importlib
import sys

attr = sys.argv[1]
config = importlib.import_module("config")
value = getattr(config, attr, None)
if value is None:
    print("")
else:
    print(value)
PY
}

is_truthy() {
  local value="${1:-}"

  value="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"

  case "$value" in
    1|true|yes|on)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

if [[ -z "${WRAPPER_PREP_CUTOFF_SEC:-}" ]]; then
  WRAPPER_PREP_CUTOFF_SEC="$(load_config_value "RACE_WRAPPER_PREP_CUTOFF_SEC")"
fi

if [[ -z "${EMULATOR_HEADLESS:-}" ]]; then
  EMULATOR_HEADLESS="$(load_config_value "EMULATOR_HEADLESS")"
fi

PREP_DEADLINE_EPOCH=""
if [[ -n "${WRAPPER_PREP_CUTOFF_SEC:-}" ]]; then
  PREP_DEADLINE_EPOCH=$((SCRIPT_START_EPOCH + WRAPPER_PREP_CUTOFF_SEC))
  echo "[$(date +"%F %T")] Wrapper prep cutoff: ${WRAPPER_PREP_CUTOFF_SEC}s"
fi

case "$MODE" in
  race)
    ;;
  *)
    echo "[$(date +"%F %T")] Unsupported mode: $MODE"
    echo "[$(date +"%F %T")] Use: race"
    exit 1
    ;;
esac

RUN_DAY_EVAL="$(
  python3 - <<'PY'
from datetime import datetime
import config

weekday_aliases = {
    "mon": "monday",
    "monday": "monday",
    "tue": "tuesday",
    "tues": "tuesday",
    "tuesday": "tuesday",
    "wed": "wednesday",
    "wednesday": "wednesday",
    "thu": "thursday",
    "thur": "thursday",
    "thurs": "thursday",
    "thursday": "thursday",
    "fri": "friday",
    "friday": "friday",
    "sat": "saturday",
    "saturday": "saturday",
    "sun": "sunday",
    "sunday": "sunday",
}

today_name = datetime.now().strftime("%A")
allowed_weekdays = getattr(config, "RUN_ONLY_ON_WEEKDAYS", None)

if not allowed_weekdays:
    print(f"allow|No weekday restriction configured. Today={today_name}")
    raise SystemExit
if isinstance(allowed_weekdays, str):
    allowed_weekdays = [allowed_weekdays]

normalized_allowed = []
invalid_entries = []
for raw_value in allowed_weekdays:
    normalized_value = weekday_aliases.get(str(raw_value).strip().lower())
    if normalized_value:
        normalized_allowed.append(normalized_value)
    else:
        invalid_entries.append(str(raw_value))

if invalid_entries:
    print(f"invalid|Invalid RUN_ONLY_ON_WEEKDAYS entries: {', '.join(invalid_entries)}")
    raise SystemExit

normalized_today = weekday_aliases[today_name.lower()]
if normalized_today in normalized_allowed:
    print(f"allow|Today={today_name} is allowed by RUN_ONLY_ON_WEEKDAYS")
else:
    print(f"skip|Today={today_name} is not in RUN_ONLY_ON_WEEKDAYS={', '.join(str(v) for v in allowed_weekdays)}")
PY
)"

IFS='|' read -r RUN_DAY_STATUS RUN_DAY_MESSAGE <<< "$RUN_DAY_EVAL"

case "$RUN_DAY_STATUS" in
  allow)
    echo "[$(date +"%F %T")] $RUN_DAY_MESSAGE"
    ;;
  skip)
    echo "[$(date +"%F %T")] $RUN_DAY_MESSAGE"
    append_automation_log "run_day_guard" "skipped" "$RUN_DAY_MESSAGE"
    exit 0
    ;;
  invalid)
    echo "[$(date +"%F %T")] $RUN_DAY_MESSAGE"
    append_automation_log "run_day_guard" "failure" "$RUN_DAY_MESSAGE"
    exit 1
    ;;
  *)
    echo "[$(date +"%F %T")] Unexpected run-day evaluation output: ${RUN_DAY_EVAL:-empty}"
    append_automation_log "run_day_guard" "failure" "Unexpected run-day evaluation output"
    exit 1
    ;;
esac

TIMEOUT_BIN=""
if command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_BIN="gtimeout"
elif command -v timeout >/dev/null 2>&1; then
  TIMEOUT_BIN="timeout"
fi

run_with_timeout() {
  local sec="$1"
  shift
  if [[ -n "$TIMEOUT_BIN" ]]; then
    "$TIMEOUT_BIN" "$sec" "$@"
  else
    "$@"
  fi
}

abort_if_wrapper_prep_too_slow() {
  local stage="$1"
  if [[ -z "${PREP_DEADLINE_EPOCH:-}" ]]; then
    return 0
  fi

  local now elapsed_sec
  now="$(date +%s)"
  if (( now < PREP_DEADLINE_EPOCH )); then
    return 0
  fi

  elapsed_sec=$((now - SCRIPT_START_EPOCH))
  echo "[$(date +"%F %T")] Wrapper prep cutoff hit after ${elapsed_sec}s while ${stage}. Aborting run."
  exit 1
}

adb_shell_probe() {
  local output
  output="$(run_with_timeout "$ADB_CMD_TIMEOUT_SEC" adb -s "$EMULATOR_SERIAL" shell echo ping 2>/dev/null | tr -d '\r')" || return 1
  [[ "$output" == "ping" ]]
}

wait_for_stable_adb() {
  local deadline=$((SECONDS + ADB_STABLE_TIMEOUT_SEC))
  local stable_hits=0
  local reconnected=0

  while [[ $SECONDS -lt $deadline ]]; do
    local state
    state="$(adb -s "$EMULATOR_SERIAL" get-state 2>/dev/null || true)"

    if [[ "$state" == "device" ]] && adb_shell_probe; then
      stable_hits=$((stable_hits + 1))
      if [[ $stable_hits -ge $ADB_STABLE_SUCCESS_COUNT ]]; then
        echo "[$(date +"%F %T")] Emulator adb is stable (${stable_hits} consecutive shell probes)"
        return 0
      fi
    else
      stable_hits=0
      if [[ $reconnected -eq 0 ]]; then
        echo "[$(date +"%F %T")] Emulator adb is not stable yet. Attempting adb reconnect."
        run_with_timeout "$ADB_CMD_TIMEOUT_SEC" adb reconnect offline >/dev/null 2>&1 || true
        run_with_timeout "$ADB_CMD_TIMEOUT_SEC" adb -s "$EMULATOR_SERIAL" wait-for-device >/dev/null 2>&1 || true
        reconnected=1
      fi
    fi

    sleep 1
  done

  return 1
}

# 2) Ensure emulator running.
DEVICE_STAGE_START_EPOCH="$(date +%s)"
get_running_emulator() {
  adb devices | awk '/^emulator-[0-9]+[[:space:]]+device$/ {print $1; exit}'
}

EMULATOR_SERIAL="$(get_running_emulator || true)"
EMULATOR_STARTED=0

if [[ -z "$EMULATOR_SERIAL" ]]; then
  EMULATOR_STARTED=1
  EMULATOR_ARGS=(
    -avd "$AVD_NAME"
    -no-snapshot-load
    -no-boot-anim
  )

  if is_truthy "${EMULATOR_HEADLESS:-}"; then
    EMULATOR_ARGS+=(-no-window)
  fi

  echo "[$(date +"%F %T")] No running emulator detected. Starting AVD: $AVD_NAME"
  echo "[$(date +"%F %T")] Emulator headless mode: ${EMULATOR_HEADLESS:-disabled}"
  nohup emulator "${EMULATOR_ARGS[@]}" > "$EMULATOR_LOG_DIR/emulator_$RUN_TS.log" 2>&1 &

  deadline=$((SECONDS + EMULATOR_BOOT_TIMEOUT_SEC))
  while [[ $SECONDS -lt $deadline ]]; do
    abort_if_wrapper_prep_too_slow "waiting for emulator to appear in adb"
    EMULATOR_SERIAL="$(get_running_emulator || true)"
    if [[ -n "$EMULATOR_SERIAL" ]]; then
      break
    fi
    sleep 2
  done
fi

if [[ -z "$EMULATOR_SERIAL" ]]; then
  echo "[$(date +"%F %T")] Emulator failed to appear in adb within timeout"
  exit 1
fi

echo "[$(date +"%F %T")] Emulator detected: $EMULATOR_SERIAL"
export ANDROID_SERIAL="$EMULATOR_SERIAL"
echo "[$(date +"%F %T")] ANDROID_SERIAL pinned to $ANDROID_SERIAL"

echo "[$(date +"%F %T")] Waiting for boot completion"

get_boot_completed_prop() {
  run_with_timeout "$ADB_CMD_TIMEOUT_SEC" adb -s "$EMULATOR_SERIAL" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r'
}

deadline=$((SECONDS + EMULATOR_BOOT_TIMEOUT_SEC))
while [[ $SECONDS -lt $deadline ]]; do
  abort_if_wrapper_prep_too_slow "waiting for emulator boot completion"
  boot="$(get_boot_completed_prop || true)"
  if [[ "$boot" == "1" ]]; then
    echo "[$(date +"%F %T")] Emulator boot completed"
    break
  fi
  sleep 2
done

if [[ "$(get_boot_completed_prop || true)" != "1" ]]; then
  echo "[$(date +"%F %T")] Emulator did not finish booting in time"
  exit 1
fi

if [[ "$EMULATOR_STARTED" -eq 1 ]]; then
  echo "[$(date +"%F %T")] Stabilizing emulator for ${POST_EMULATOR_BOOT_STABILIZE_SEC}s"
  sleep "$POST_EMULATOR_BOOT_STABILIZE_SEC"
fi

# Bring device into a predictable state for unattended runs.
echo "[$(date +"%F %T")] Waking and unlocking emulator"
run_with_timeout "$ADB_CMD_TIMEOUT_SEC" adb -s "$EMULATOR_SERIAL" wait-for-device || true
run_with_timeout "$ADB_CMD_TIMEOUT_SEC" adb -s "$EMULATOR_SERIAL" shell input keyevent 224 || true
run_with_timeout "$ADB_CMD_TIMEOUT_SEC" adb -s "$EMULATOR_SERIAL" shell input keyevent 82 || true
run_with_timeout "$ADB_CMD_TIMEOUT_SEC" adb -s "$EMULATOR_SERIAL" shell input keyevent 3 || true
sleep 2
echo "[$(date +"%F %T")] Emulator unlock sequence done"

# Disable system animations so screen transitions are instant and the UI reaches
# an idle state sooner — this complements the UiAutomator2 waitForIdle tuning and
# shaves latency off every interaction during the booking race.
if is_truthy "$(load_config_value "DISABLE_EMULATOR_ANIMATIONS")"; then
  echo "[$(date +"%F %T")] Disabling emulator animations"
  run_with_timeout "$ADB_CMD_TIMEOUT_SEC" adb -s "$EMULATOR_SERIAL" shell settings put global window_animation_scale 0 || true
  run_with_timeout "$ADB_CMD_TIMEOUT_SEC" adb -s "$EMULATOR_SERIAL" shell settings put global transition_animation_scale 0 || true
  run_with_timeout "$ADB_CMD_TIMEOUT_SEC" adb -s "$EMULATOR_SERIAL" shell settings put global animator_duration_scale 0 || true
fi

DEVICE_STAGE_END_EPOCH="$(date +%s)"
DEVICE_STAGE_ELAPSED_SEC=$((DEVICE_STAGE_END_EPOCH - DEVICE_STAGE_START_EPOCH))
echo "[$(date +"%F %T")] Device ready after ${DEVICE_STAGE_ELAPSED_SEC}s ($(format_elapsed "$DEVICE_STAGE_ELAPSED_SEC"))"
append_automation_log "device_start" "success" "elapsed_sec=${DEVICE_STAGE_ELAPSED_SEC} fmt=$(format_elapsed "$DEVICE_STAGE_ELAPSED_SEC")"

# 3) Ensure Appium running.
APPIUM_STAGE_START_EPOCH="$(date +%s)"
appium_up() {
  curl --connect-timeout 2 --max-time 5 -fsS "http://$APPIUM_HOST:$APPIUM_PORT/status" >/dev/null 2>&1
}

port_listener_pid() {
  lsof -nP -iTCP:"$APPIUM_PORT" -sTCP:LISTEN -t 2>/dev/null | head -n 1
}

reap_stale_appium_on_port() {
  local pid
  pid="$(port_listener_pid || true)"
  if [[ -z "${pid:-}" ]]; then
    return
  fi

  local cmdline
  cmdline="$(ps -p "$pid" -o command= 2>/dev/null || true)"

  if [[ "$cmdline" == *appium* ]]; then
    echo "[$(date +"%F %T")] Found stale Appium on port $APPIUM_PORT (pid=$pid). Restarting it."
    kill "$pid" >/dev/null 2>&1 || true
    sleep 2
    if ps -p "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
      sleep 1
    fi
  else
    echo "[$(date +"%F %T")] Port $APPIUM_PORT is in use by non-Appium process (pid=$pid)."
    echo "[$(date +"%F %T")] Command: ${cmdline:-unknown}"
    echo "[$(date +"%F %T")] Free that port or run with a different APPIUM_PORT."
    exit 1
  fi
}

if appium_up; then
  echo "[$(date +"%F %T")] Appium already running on $APPIUM_HOST:$APPIUM_PORT"
else
  reap_stale_appium_on_port
  echo "[$(date +"%F %T")] Starting Appium on $APPIUM_HOST:$APPIUM_PORT"
  APPIUM_LOG="$APPIUM_LOG_DIR/appium_$RUN_TS.log"
  nohup appium --address "$APPIUM_HOST" --port "$APPIUM_PORT" > "$APPIUM_LOG" 2>&1 &
  APPIUM_PID=$!
  echo "[$(date +"%F %T")] Appium pid=$APPIUM_PID log=$APPIUM_LOG"

  deadline=$((SECONDS + APPIUM_START_TIMEOUT_SEC))
  next_progress=$SECONDS
  until appium_up || [[ $SECONDS -ge $deadline ]]; do
    abort_if_wrapper_prep_too_slow "waiting for Appium to become ready"
    if ! ps -p "$APPIUM_PID" >/dev/null 2>&1; then
      echo "[$(date +"%F %T")] Appium process exited early (pid=$APPIUM_PID)."
      if [[ -f "$APPIUM_LOG" ]]; then
        echo "[$(date +"%F %T")] Last appium log lines:"
        tail -n 40 "$APPIUM_LOG" || true
      fi
      exit 1
    fi
    if [[ $SECONDS -ge $next_progress ]]; then
      remaining=$((deadline - SECONDS))
      echo "[$(date +"%F %T")] Waiting for Appium... ${remaining}s left"
      next_progress=$((SECONDS + 5))
    fi
    sleep 1
  done

  if ! appium_up; then
    echo "[$(date +"%F %T")] Appium failed to start within timeout"
    if [[ -f "$APPIUM_LOG" ]]; then
      echo "[$(date +"%F %T")] Last appium log lines:"
      tail -n 40 "$APPIUM_LOG" || true
    fi
    exit 1
  fi

  echo "[$(date +"%F %T")] Stabilizing Appium for ${POST_APPIUM_START_STABILIZE_SEC}s"
  sleep "$POST_APPIUM_START_STABILIZE_SEC"
fi

echo "[$(date +"%F %T")] Appium ready"
APPIUM_STAGE_END_EPOCH="$(date +%s)"
APPIUM_STAGE_ELAPSED_SEC=$((APPIUM_STAGE_END_EPOCH - APPIUM_STAGE_START_EPOCH))
echo "[$(date +"%F %T")] Appium ready after ${APPIUM_STAGE_ELAPSED_SEC}s ($(format_elapsed "$APPIUM_STAGE_ELAPSED_SEC"))"
append_automation_log "appium_start" "success" "elapsed_sec=${APPIUM_STAGE_ELAPSED_SEC} fmt=$(format_elapsed "$APPIUM_STAGE_ELAPSED_SEC")"

# Final adb readiness gate to reduce "device offline" session failures.
echo "[$(date +"%F %T")] Verifying emulator adb stability before Python launch"
abort_if_wrapper_prep_too_slow "verifying emulator adb stability"
if ! wait_for_stable_adb; then
  echo "[$(date +"%F %T")] Emulator adb did not become stable in time (state=$(adb -s "$EMULATOR_SERIAL" get-state 2>/dev/null || true)). Exiting."
  exit 1
fi

# 4) Run python booking flow (its own logs/screenshots still apply).
abort_if_wrapper_prep_too_slow "preparing to launch Python automation"
echo "[$(date +"%F %T")] Launching python automation"
cd "$PROJECT_DIR"
# Hand the wrapper-stage timings to Python so its consolidated phase_timing log
# line can include device_start and appium_start alongside the in-app phases.
export DEVICE_STAGE_ELAPSED_SEC
export APPIUM_STAGE_ELAPSED_SEC
PYTHON_STAGE_START_EPOCH="$(date +%s)"
python3 main.py "$MODE"
PYTHON_STAGE_END_EPOCH="$(date +%s)"
PYTHON_STAGE_ELAPSED_SEC=$((PYTHON_STAGE_END_EPOCH - PYTHON_STAGE_START_EPOCH))
echo "[$(date +"%F %T")] Python automation finished in ${PYTHON_STAGE_ELAPSED_SEC}s ($(format_elapsed "$PYTHON_STAGE_ELAPSED_SEC"))"
append_automation_log "python_stage" "success" "elapsed_sec=${PYTHON_STAGE_ELAPSED_SEC} fmt=$(format_elapsed "$PYTHON_STAGE_ELAPSED_SEC")"

echo "[$(date +"%F %T")] Run finished successfully"
