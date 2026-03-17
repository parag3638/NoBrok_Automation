# from booking import run
# import sys


# if __name__ == "__main__":
#     ok, message = run()
#     if ok:
#         print(f"[SUCCESS] {message}")
#     else:
#         print(f"[FAILED] {message}")
#         sys.exit(1)


import sys
from booking import prewarm, run, run_hot


if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "full"

    if mode == "prewarm":
        ok, message = prewarm()
    elif mode == "hot":
        ok, message = run_hot()
    elif mode == "full":
        ok, message = run()
    else:
        print(f"[FAILED] Unknown mode: {mode}. Use one of: full, prewarm, hot")
        sys.exit(1)

    if ok:
        print(f"[SUCCESS] {message}")
    else:
        print(f"[FAILED] {message}")
        sys.exit(1)