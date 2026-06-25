from datetime import datetime
from pathlib import Path
import re

LOG_DIR = Path("logs")
AUTOMATION_LOG = LOG_DIR / "automation.log"
PAGE_SOURCE_DIR = LOG_DIR / "page_sources"
SCREENSHOT_ROOT = Path("screenshots")
SUCCESS_DIR = SCREENSHOT_ROOT / "success"
FAILURE_DIR = SCREENSHOT_ROOT / "failure"


def ensure_dirs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_DIR.mkdir(parents=True, exist_ok=True)
    FAILURE_DIR.mkdir(parents=True, exist_ok=True)


def write_log(step, status, selected_slot="-", details=""):
    ensure_dirs()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = (
        f"{timestamp} | step={step} | status={status} | "
        f"slot={selected_slot} | details={details}\n"
    )
    with AUTOMATION_LOG.open("a", encoding="utf-8") as log_file:
        log_file.write(line)


def capture_screenshot(driver, status, label):
    ensure_dirs()
    target_dir = SUCCESS_DIR if status == "success" else FAILURE_DIR
    safe_label = re.sub(r"[^a-zA-Z0-9_-]+", "_", label).strip("_") or "snapshot"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = target_dir / f"{safe_label}_{timestamp}.png"
    try:
        driver.save_screenshot(str(path))
        print(f"Screenshot saved: {path}")
        return path
    except Exception as exc:
        print(f"Screenshot skipped for {safe_label}: {type(exc).__name__}: {exc}")
        return None


def dump_page_source(driver, label):
    """Save the current Appium page source XML for after-the-fact debugging.

    Best-effort: never raises, so it is safe to call from failure paths.
    """
    PAGE_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    safe_label = re.sub(r"[^a-zA-Z0-9_-]+", "_", label).strip("_") or "snapshot"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = PAGE_SOURCE_DIR / f"{safe_label}_{timestamp}.xml"
    try:
        source = driver.page_source
    except Exception as exc:
        print(f"Page source dump skipped for {safe_label}: {type(exc).__name__}: {exc}")
        return None
    try:
        path.write_text(source, encoding="utf-8")
        print(f"Page source saved: {path}")
        return path
    except Exception as exc:
        print(f"Page source write failed for {safe_label}: {type(exc).__name__}: {exc}")
        return None


def write_alert(message, alert_file):
    ensure_dirs()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path = Path(alert_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{timestamp} | ALERT | {message}\n")
    print(f"Alert written: {path}")
