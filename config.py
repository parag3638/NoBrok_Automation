APPIUM_URL = "http://127.0.0.1:4723"
PACKAGE = "com.app.nobrokerhood"
ACTIVITY = ".activities.DoorSplashScreen"
PLATFORM_NAME = "Android"
DEVICE_NAME = "Android Emulator"
AUTOMATION_NAME = "UiAutomator2"
NO_RESET = True
SESSION_NEW_COMMAND_TIMEOUT_SEC = 300
UIAUTOMATOR2_SERVER_LAUNCH_TIMEOUT_MS = 90000
UIAUTOMATOR2_SERVER_INSTALL_TIMEOUT_MS = 90000
ADB_EXEC_TIMEOUT_MS = 90000
APPIUM_SESSION_CREATE_RETRIES = 2
APPIUM_SESSION_RETRY_DELAY_SEC = 5

# UiAutomator2 driver settings applied right after the session is created.
#
# MEASURED FINDING (dry-run A/B, 2026-06-25): lowering waitForIdleTimeout does NOT
# speed up this app. The ~750ms/interaction is the app's own network+render
# latency, not the UiAutomator2 idle wait — stock (10000) and tuned (100) gave the
# same post-trigger timings, and idle=0 actively broke navigation (taps fired on a
# still-scrolling list). So this is treated as a SAFETY CAP, not a speedup: 1500ms
# is comfortably above the observed ~750ms settle time (so it never truncates a
# real transition or misfires) while capping pathological "never idle" screens
# well below the 10s stock default. Set to 10000 to fully restore stock behaviour.
UIA2_WAIT_FOR_IDLE_TIMEOUT_MS = 1500
UIA2_ACTION_ACK_TIMEOUT_MS = 3000
# ignoreUnimportantViews can hide elements from the finder; keep it off (Appium
# default) unless a measured need arises.
UIA2_IGNORE_UNIMPORTANT_VIEWS = False
DISABLE_WINDOW_ANIMATION = True
# Read by run.sh (via load_config_value) to zero out emulator animator scales.
DISABLE_EMULATOR_ANIMATIONS = True


EMULATOR_HEADLESS = True
# EMULATOR_HEADLESS = False


WAIT_SEC = 12
CLICK_RETRIES = 2
RETRY_DELAY_SEC = 1
HOME_NAV_RETRIES = 3
HOME_OVERLAY_DISMISS_WAIT_SEC = 0.5
HOME_OVERLAY_PAGE_SOURCE_KEYWORDS = [
    "looking to sell something",
    "society marketplace",
    "list now",
    "lifetime free",
    "zero forex",
    "goldx",
    "uni bobcard",
    "shop now",
    "sale",
    "ajio",
    "superdry",
    "u.s. polo",
    "instant discount",
]


HOME_OVERLAY_CLOSE_HOTSPOTS = [
    (0.50, 0.42),
    (0.50, 0.44),
    (0.50, 0.49),
    (0.50, 0.46),
]


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


# Set to `None` or `[]` to allow automation on every day.
# Accepted values: "Mon", "Monday", "Tue", "Tuesday", etc.
# RUN_ONLY_ON_WEEKDAYS = ["Monday"]


RUN_ONLY_ON_WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


PREFERRED_COURTS = [
    "Lawn Tennis Parcel 5",
    "Lawn Tennis Parcel 6",
]

# Release-specific slot target.
# Keys are booking release times in 24h format.
# Each release maps to the exact tomorrow slot to attempt first.

RELEASE_SLOT_MAP = {
    # "12:00": {
    #     "window": "Afternoon",
    #     "slot": "01:00 - 02:00",
    # },
    # "19:00": {
    #     "window": "Evening",
    #     "slot": "08:00 - 09:00",
    # },
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

# RACE_TEST_TRIGGER_AFTER_SEC = 20
RACE_TEST_TRIGGER_AFTER_SEC = None
RACE_TEST_PROFILE = {
    "window": "Afternoon",
    "slot": "03:00 - 04:00",
}

RACE_DAY_HOLD = "Today"
RACE_POLL_INTERVAL_SEC = 1.0
RACE_FINAL_POLL_INTERVAL_SEC = 0.5
RACE_FINAL_WINDOW_SEC = 10
RACE_LAST_MILE_WINDOW_SEC = 3
RACE_LAST_MILE_POLL_INTERVAL_SEC = 0.25
RACE_REFRESH_RETRY_TIMEOUT_SEC = 8
RACE_MAX_PRE_RELEASE_WAIT_SEC = 600
# Abort the shell wrapper if emulator/Appium prep takes too long before Python starts.
# Set to None to disable this cutoff.
RACE_WRAPPER_PREP_CUTOFF_SEC = 90
RACE_PROGRESS_LOG_INTERVAL_SEC = 5
RACE_SESSION_KEEPALIVE_INTERVAL_SEC = 15
RACE_SLOT_TIMEOUT_SEC = 0.75
RACE_SLOT_UNAVAILABLE_POPUP_WAIT_SEC = 0.45
RACE_POST_CAPACITY_STABILIZE_SEC = 0
RACE_FAMILY_ACTION_TIMEOUT_SEC = 1.5
RACE_CONFIRM_BUTTON_TIMEOUT_SEC = 2
RACE_REQUIRE_CONFIRMATION = True
RACE_BOOKING_LIST_VERIFY_TIMEOUT_SEC = 20
RACE_BOOKING_LIST_VERIFY_POLL_SEC = 1
EXIT_AFTER_BOOK_CLICK = False
POST_BOOK_CLICK_EXIT_DELAY_SEC = 3
DRY_RUN_SKIP_BOOKING = False

# When True, failure paths (and rejected-grab decision points) dump the current
# Appium page source XML into logs/page_sources/ alongside a screenshot, so an
# after-the-fact run can be debugged from what the app actually showed.
SAVE_PAGE_SOURCE_ON_FAILURE = True


FAMILY_MEMBERS = ["Parag", "Sayel Chakraborty", "Manav Grover"]
MIN_CAPACITY = 3
