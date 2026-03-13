from booking import run
import sys


if __name__ == "__main__":
    ok, message = run()
    if ok:
        print(f"[SUCCESS] {message}")
    else:
        print(f"[FAILED] {message}")
        sys.exit(1)
