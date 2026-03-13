
#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/predator258/NoBrok_Automation"

if [[ $# -ge 1 ]]; then
  MODE="$1"
else
  CURRENT_HHMM="$(date +%H%M)"
  case "$CURRENT_HHMM" in
    1858)
      MODE="prewarm"
      ;;
    1900)
      MODE="hot"
      ;;
    *)
      echo "Unsupported launch time: $CURRENT_HHMM"
      exit 1
      ;;
  esac
fi

cd "$PROJECT_DIR"
exec /usr/bin/caffeinate -i "$PROJECT_DIR/run.sh" "$MODE"
