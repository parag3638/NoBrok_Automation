import sys
from booking import run_race


if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "race"

    if mode == "race":
        ok, message = run_race()
    else:
        print(f"[FAILED] Unknown mode: {mode}. Use: race")
        sys.exit(1)

    if ok:
        print(f"[SUCCESS] {message}")
    else:
        print(f"[FAILED] {message}")
        sys.exit(1)
