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

# Runtime knobs (override via env if needed)
: "${AVD_NAME:=Pixel_7}"
: "${APPIUM_HOST:=127.0.0.1}"
: "${APPIUM_PORT:=4723}"
: "${EMULATOR_BOOT_TIMEOUT_SEC:=240}"
: "${APPIUM_START_TIMEOUT_SEC:=60}"
: "${POST_EMULATOR_BOOT_STABILIZE_SEC:=5}"
: "${POST_APPIUM_START_STABILIZE_SEC:=5}"
: "${ADB_CMD_TIMEOUT_SEC:=12}"

mkdir -p \
  "$LOG_DIR" \
  "$RUN_LOG_DIR" \
  "$APPIUM_LOG_DIR" \
  "$EMULATOR_LOG_DIR" \
  "$SCREENSHOT_DIR/success" \
  "$SCREENSHOT_DIR/failure"

# Send this wrapper's output to both terminal and run log.
exec > >(tee -a "$RUN_LOG") 2>&1

echo "[$(date +"%F %T")] Run started"
echo "[$(date +"%F %T")] Run log: $RUN_LOG"

cleanup() {
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
  echo "[$(date +"%F %T")] Lock removed"
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

require_cmd python3
require_cmd adb
require_cmd emulator
require_cmd curl
require_cmd appium
require_cmd lsof

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

# 2) Ensure emulator running.
get_running_emulator() {
  adb devices | awk '/^emulator-[0-9]+[[:space:]]+device$/ {print $1; exit}'
}

EMULATOR_SERIAL="$(get_running_emulator || true)"
EMULATOR_STARTED=0

if [[ -z "$EMULATOR_SERIAL" ]]; then
  EMULATOR_STARTED=1
  echo "[$(date +"%F %T")] No running emulator detected. Starting AVD: $AVD_NAME"
  nohup emulator -avd "$AVD_NAME" -no-snapshot-load -no-boot-anim > "$EMULATOR_LOG_DIR/emulator_$RUN_TS.log" 2>&1 &

  deadline=$((SECONDS + EMULATOR_BOOT_TIMEOUT_SEC))
  while [[ $SECONDS -lt $deadline ]]; do
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

deadline=$((SECONDS + EMULATOR_BOOT_TIMEOUT_SEC))
while [[ $SECONDS -lt $deadline ]]; do
  boot="$(adb -s "$EMULATOR_SERIAL" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')"
  if [[ "$boot" == "1" ]]; then
    echo "[$(date +"%F %T")] Emulator boot completed"
    break
  fi
  sleep 2
done

if [[ "$(adb -s "$EMULATOR_SERIAL" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" != "1" ]]; then
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

# 3) Ensure Appium running.
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

# Final adb readiness gate to reduce "device offline" session failures.
echo "[$(date +"%F %T")] Verifying emulator device state before Python launch"
deadline=$((SECONDS + 30))
while [[ $SECONDS -lt $deadline ]]; do
  state="$(adb -s "$EMULATOR_SERIAL" get-state 2>/dev/null || true)"
  if [[ "$state" == "device" ]]; then
    echo "[$(date +"%F %T")] Emulator state is online: $state"
    break
  fi
  sleep 1
done

if [[ "$(adb -s "$EMULATOR_SERIAL" get-state 2>/dev/null || true)" != "device" ]]; then
  echo "[$(date +"%F %T")] Emulator is not online (state=$(adb -s "$EMULATOR_SERIAL" get-state 2>/dev/null || true)). Exiting."
  exit 1
fi

# 4) Run python booking flow (its own logs/screenshots still apply).
echo "[$(date +"%F %T")] Launching python automation"
cd "$PROJECT_DIR"
python3 main.py

echo "[$(date +"%F %T")] Run finished successfully"
