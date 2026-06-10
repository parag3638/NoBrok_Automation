import sys
from datetime import datetime

import config
from booking import run_race
from logger import write_log


WEEKDAY_ALIASES = {
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


def evaluate_run_day(now=None):
    now = now or datetime.now()
    today_name = now.strftime("%A")
    allowed_weekdays = getattr(config, "RUN_ONLY_ON_WEEKDAYS", None)

    if not allowed_weekdays:
        return "allow", f"No weekday restriction configured. Today={today_name}"
    if isinstance(allowed_weekdays, str):
        allowed_weekdays = [allowed_weekdays]

    normalized_allowed = []
    invalid_entries = []
    for raw_value in allowed_weekdays:
        normalized_value = WEEKDAY_ALIASES.get(str(raw_value).strip().lower())
        if normalized_value:
            normalized_allowed.append(normalized_value)
        else:
            invalid_entries.append(str(raw_value))

    if invalid_entries:
        invalid_values = ", ".join(invalid_entries)
        return "invalid", f"Invalid RUN_ONLY_ON_WEEKDAYS entries: {invalid_values}"

    normalized_today = WEEKDAY_ALIASES[today_name.lower()]
    if normalized_today in normalized_allowed:
        return "allow", f"Today={today_name} is allowed by RUN_ONLY_ON_WEEKDAYS"

    configured_days = ", ".join(allowed_weekdays)
    return "skip", f"Today={today_name} is not in RUN_ONLY_ON_WEEKDAYS={configured_days}"


if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "race"

    run_day_status, run_day_message = evaluate_run_day()
    if run_day_status == "invalid":
        write_log("run_day_guard", "failure", details=run_day_message)
        print(f"[FAILED] {run_day_message}")
        sys.exit(1)
    if run_day_status == "skip":
        write_log("run_day_guard", "skipped", details=run_day_message)
        print(f"[SKIPPED] {run_day_message}")
        sys.exit(0)

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
