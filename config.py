APPIUM_URL = "http://127.0.0.1:4723"
PACKAGE = "com.app.nobrokerhood"
ACTIVITY = ".activities.DoorSplashScreen"
PLATFORM_NAME = "Android"
DEVICE_NAME = "Android Emulator"
AUTOMATION_NAME = "UiAutomator2"
NO_RESET = True
SESSION_NEW_COMMAND_TIMEOUT_SEC = 300

WAIT_SEC = 12
CLICK_RETRIES = 2
RETRY_DELAY_SEC = 1
PER_SLOT_TIMEOUT_SEC = 6
EMPTY_STATE_RECHECK_ENABLED = True
EMPTY_STATE_RECHECK_SEC = 0.25
BOOKING_CONFIRM_TIMEOUT_SEC = 12
BOOKING_CONFIRM_POLL_SEC = 1
APP_FOREGROUND_RETRIES = 3
APP_LAUNCH_STABILIZE_SEC = 3
POST_CAPACITY_STABILIZE_SEC = 5
HOT_POST_CAPACITY_STABILIZE_SEC = 0.5

SESSION_GUARD_ENABLED = True
SESSION_GUARD_PAGE_SOURCE_TIMEOUT_SEC = 0.5
LOGIN_SCREEN_KEYWORDS = [
    "login",
    "log in",
    "otp",
    "enter mobile",
    "continue with mobile",
    "sign in",
]
SESSION_ALERT_FILE = "logs/ALERT_LOGIN_REQUIRED.txt"

SPORT = "Lawn Tennis"
DAY = "Tomorrow"
PREFERRED_COURTS = [
    "Lawn Tennis Parcel 5",
    "Lawn Tennis Parcel 6",
]

# Release-specific slot target.
# Keys are booking release times in 24h format.
# Each release maps to the exact tomorrow slot to attempt first.
RELEASE_SLOT_MAP = {
    "12:00": {
        "window": "Afternoon",
        "slot": "01:00 - 02:00",
    },
    "19:00": {
        "window": "Evening",
        "slot": "08:00 - 09:00",
    },
    "20:00": {
        "window": "Evening",
        "slot": "09:00 - 10:00",
    },
}

# Optional ad-hoc test override.
# Set RACE_TEST_TRIGGER_AFTER_SEC to an integer like 90 to make race mode
# fire after that many seconds instead of waiting for the next release in RELEASE_SLOT_MAP.
# Set it back to None for scheduled production runs.
# RACE_TEST_TRIGGER_AFTER_SEC = 20
RACE_TEST_TRIGGER_AFTER_SEC = None
# RACE_TEST_TRIGGER_AFTER_SEC = 20
RACE_TEST_PROFILE = {
    "window": "Morning",
    "slot": "09:00 - 10:00",
}

RACE_DAY_HOLD = "Today"
RACE_POLL_INTERVAL_SEC = 1.0
RACE_FINAL_POLL_INTERVAL_SEC = 0.5
RACE_FINAL_WINDOW_SEC = 10
RACE_LAST_MILE_WINDOW_SEC = 3
RACE_LAST_MILE_POLL_INTERVAL_SEC = 0.25
RACE_REFRESH_RETRY_TIMEOUT_SEC = 8
RACE_PROGRESS_LOG_INTERVAL_SEC = 5
RACE_SESSION_KEEPALIVE_INTERVAL_SEC = 15
RACE_SLOT_TIMEOUT_SEC = 0.75
RACE_SLOT_UNAVAILABLE_POPUP_WAIT_SEC = 0.45
RACE_POST_CAPACITY_STABILIZE_SEC = 0
RACE_FAMILY_ACTION_TIMEOUT_SEC = 1.5
RACE_CONFIRM_BUTTON_TIMEOUT_SEC = 2
RACE_REQUIRE_CONFIRMATION = False


FAMILY_MEMBERS = ["Parag", "Sayel Chakraborty", "Manav Grover"]
MIN_CAPACITY = 2
