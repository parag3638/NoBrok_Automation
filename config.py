# APPIUM_URL = "http://127.0.0.1:4723"
# PACKAGE = "com.app.nobrokerhood"
# ACTIVITY = ".activities.DoorSplashScreen"
# PLATFORM_NAME = "Android"
# DEVICE_NAME = "Android Emulator"
# AUTOMATION_NAME = "UiAutomator2"
# NO_RESET = True

# WAIT_SEC = 12
# CLICK_RETRIES = 2
# RETRY_DELAY_SEC = 1
# PER_SLOT_TIMEOUT_SEC = 6
# BOOKING_CONFIRM_TIMEOUT_SEC = 12
# BOOKING_CONFIRM_POLL_SEC = 1
# APP_FOREGROUND_RETRIES = 3
# APP_LAUNCH_STABILIZE_SEC = 3

# SESSION_GUARD_ENABLED = True
# SESSION_GUARD_PAGE_SOURCE_TIMEOUT_SEC = 3
# LOGIN_SCREEN_KEYWORDS = [
#     "login",
#     "log in",
#     "otp",
#     "enter mobile",
#     "continue with mobile",
#     "sign in",
# ]
# SESSION_ALERT_FILE = "logs/ALERT_LOGIN_REQUIRED.txt"

# SPORT = "Lawn Tennis"
# DAY = "Tomorrow"
# PREFERRED_COURTS = [
#     "Lawn Tennis Parcel 5",
#     "Lawn Tennis Parcel 6",
# ]

# # Window-specific slot priority (tried top-to-bottom).
# # Window options: "All Slots", "Morning", "Afternoon", "Evening"
# PREFERRED_SLOTS_BY_WINDOW = {
#     "Evening": [
#         "08:00 - 09:00",
#         "09:00 - 10:00",
#     ],
#     # "Morning": [
#     #     "08:00 - 09:00",
#     #     "07:00 - 08:00",
#     # ],
# }


# FAMILY_MEMBERS = ["Parag", "Sayel Chakraborty", "Manav Grover"]
# MIN_CAPACITY = 3


APPIUM_URL = "http://127.0.0.1:4723"
PACKAGE = "com.app.nobrokerhood"
ACTIVITY = ".activities.DoorSplashScreen"
PLATFORM_NAME = "Android"
DEVICE_NAME = "Android Emulator"
AUTOMATION_NAME = "UiAutomator2"
NO_RESET = True

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

# Window-specific slot priority (tried top-to-bottom).
# Window options: "All Slots", "Morning", "Afternoon", "Evening"
PREFERRED_SLOTS_BY_WINDOW = {
    "Evening": [
        "08:00 - 09:00",
        "09:00 - 10:00",
    ],
    # "Morning": [
    #     "08:00 - 09:00",
    #     "07:00 - 08:00",
    # ],
}


FAMILY_MEMBERS = ["Parag", "Sayel Chakraborty", "Manav Grover"]
MIN_CAPACITY = 3