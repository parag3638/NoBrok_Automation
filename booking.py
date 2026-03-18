from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    InvalidSessionIdException,
)
import re
import time
import os
import subprocess
from datetime import datetime, timedelta

import config
from logger import capture_screenshot, write_alert, write_log


def safe_click(driver, locator, retries=config.CLICK_RETRIES, timeout=config.WAIT_SEC, retry_delay=config.RETRY_DELAY_SEC):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            element.click()
            return element
        except (
            TimeoutException,
            StaleElementReferenceException,
            ElementClickInterceptedException,
        ) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(retry_delay)

    raise Exception(
        f"Failed click after {retries} retries for locator: {locator}"
    ) from last_error


def wait_click(driver, locator, timeout=config.WAIT_SEC):
    return safe_click(driver, locator, retries=config.CLICK_RETRIES, timeout=timeout)


def wait_present(driver, locator, timeout=config.WAIT_SEC):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(locator)
    )


def open_app(launch_app=True):
    options = UiAutomator2Options()
    options.platform_name = config.PLATFORM_NAME
    options.device_name = config.DEVICE_NAME
    options.automation_name = config.AUTOMATION_NAME
    if launch_app:
        options.app_package = config.PACKAGE
        options.app_activity = config.ACTIVITY
    options.no_reset = config.NO_RESET
    options.set_capability("newCommandTimeout", config.SESSION_NEW_COMMAND_TIMEOUT_SEC)
    device_udid = os.getenv("ANDROID_SERIAL")
    if device_udid:
        options.udid = device_udid
    return webdriver.Remote(config.APPIUM_URL, options=options)


def ensure_app_in_foreground(driver, prefer_existing=False):
    if prefer_existing:
        try:
            if driver.current_package == config.PACKAGE:
                write_log("app_foreground", "success", details="App already in foreground")
                return
        except Exception:
            pass

    for _ in range(config.APP_FOREGROUND_RETRIES):
        try:
            driver.activate_app(config.PACKAGE)
        except Exception:
            pass

        time.sleep(config.APP_LAUNCH_STABILIZE_SEC)
        try:
            if driver.current_package == config.PACKAGE:
                write_log("app_foreground", "success", details="App is in foreground")
                return
        except Exception:
            pass

        try:
            driver.start_activity(config.PACKAGE, config.ACTIVITY)
        except Exception:
            pass

        time.sleep(config.APP_LAUNCH_STABILIZE_SEC)
        try:
            if driver.current_package == config.PACKAGE:
                write_log("app_foreground", "success", details="App launched via start_activity")
                return
        except Exception:
            pass

    capture_screenshot(driver, "failure", "app_not_foreground")
    write_log("app_foreground", "failure", details="Could not bring app to foreground")
    raise Exception("Could not bring app to foreground before automation.")


def is_login_screen_visible(driver):
    source = driver.page_source.lower()
    return any(keyword in source for keyword in config.LOGIN_SCREEN_KEYWORDS)


def enforce_session_guard(driver):
    if not config.SESSION_GUARD_ENABLED:
        return

    # Let initial screen settle before reading source for login markers.
    time.sleep(config.SESSION_GUARD_PAGE_SOURCE_TIMEOUT_SEC)
    if is_login_screen_visible(driver):
        message = "Login screen detected. Manual login required before automation run."
        capture_screenshot(driver, "failure", "login_screen_detected")
        write_log("session_guard", "failure", selected_slot="-", details=message)
        write_alert(message, config.SESSION_ALERT_FILE)
        raise Exception(message)

    write_log("session_guard", "success", selected_slot="-", details="Active session detected")


def close_app(driver):
    try:
        driver.terminate_app(config.PACKAGE)
    except Exception:
        pass
    try:
        device_udid = os.getenv("ANDROID_SERIAL")
        adb_cmd = ["adb"]
        if device_udid:
            adb_cmd.extend(["-s", device_udid])
        adb_cmd.extend(["shell", "am", "force-stop", config.PACKAGE])
        subprocess.run(adb_cmd, check=False, capture_output=True, text=True)
    except Exception:
        pass
    try:
        driver.quit()
    except Exception:
        pass


def release_driver(driver):
    try:
        driver.quit()
    except Exception:
        pass


def keep_session_alive(driver):
    try:
        current_package = driver.current_package
        write_log(
            "race_keepalive",
            "success",
            selected_slot="-",
            details=f"package={current_package}",
        )
    except InvalidSessionIdException as exc:
        raise Exception("Appium session expired while waiting for release boundary.") from exc
    except Exception:
        # Keepalive is best-effort; transient failures should not abort the wait loop.
        pass


def format_elapsed_sec(elapsed_sec):
    total_sec = max(0, int(round(elapsed_sec)))
    return f"{total_sec}s ({total_sec // 3600:02d}:{(total_sec % 3600) // 60:02d}:{total_sec % 60:02d})"


def print_timing(label, elapsed_sec):
    print(f"{label}: {elapsed_sec:.2f}s [{format_elapsed_sec(elapsed_sec)}]")


def click_element_with_fallback(driver, element):
    try:
        element.click()
    except Exception:
        driver.execute_script("mobile: clickGesture", {"elementId": element.id})


def go_to_amenities(driver):
    wait_click(driver, (AppiumBy.ACCESSIBILITY_ID, "Society"))
    wait_click(
        driver,
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("Amenities")')
    )


def open_booking_screen(driver, sport_name):
    go_to_amenities(driver)
    select_sport(driver, sport_name)
    tap_book(driver)


def select_sport(driver, sport_name):
    sport = wait_present(
        driver,
        (
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiScrollable(new UiSelector().scrollable(true))'
            f'.scrollIntoView(new UiSelector().text("{sport_name}"));'
        )
    )
    sport.click()


def tap_book(driver):
    wait_click(driver, (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("Book")'))


def select_day(driver, day_name):
    wait_click(
        driver,
        (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{day_name}")')
    )


def is_booking_screen_ready(driver, day_name):
    ready_markers = driver.find_elements(
        AppiumBy.ANDROID_UIAUTOMATOR,
        f'new UiSelector().text("{day_name}")'
    )
    return bool(ready_markers)


def select_court(driver, court_name):
    wait_click(
        driver,
        (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{court_name}")')
    )


def select_all(driver):
    wait_click(
        driver,
        (
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().resourceId("com.app.nobrokerhood:id/tvAll").text("All")'
        )
    )


def select_slot_window(driver, slot_window):
    window = slot_window.strip()
    if window.lower() in {"all", "all slots"}:
        select_all(driver)
        return

    wait_click(
        driver,
        (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().textContains("{window}")')
    )


def select_day_if_needed(driver, day_name):
    day_chip = wait_present(
        driver,
        (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{day_name}")'),
    )
    is_selected = (day_chip.get_attribute("selected") or "").lower() == "true"
    if not is_selected:
        day_chip.click()
    return day_chip


def is_no_slots_found_visible(driver):
    no_slots_title = driver.find_elements(
        AppiumBy.ANDROID_UIAUTOMATOR,
        'new UiSelector().text("No slots found")'
    )
    no_slots_message = driver.find_elements(
        AppiumBy.ANDROID_UIAUTOMATOR,
        'new UiSelector().textContains("no available slots")'
    )
    return bool(no_slots_title) or bool(no_slots_message)


def maybe_recheck_empty_slot_state(driver, slot_window, recheck_sec, enabled):
    if not enabled or recheck_sec <= 0:
        return is_no_slots_found_visible(driver)

    time.sleep(recheck_sec)
    if not is_no_slots_found_visible(driver):
        return False

    select_slot_window(driver, slot_window)
    time.sleep(recheck_sec)
    return is_no_slots_found_visible(driver)


def select_slot_with_timeout(driver, slot_text, timeout, popup_wait_sec=1.2):
    slot_locator = (
        AppiumBy.XPATH,
        "//android.view.ViewGroup[@resource-id='com.app.nobrokerhood:id/clTimeSlot'"
        " and .//android.widget.TextView"
        "[@resource-id='com.app.nobrokerhood:id/tvAvailableTimeSlot'"
        f" and @text='{slot_text}']]"
    )
    slot_element = wait_present(driver, slot_locator, timeout=timeout)

    click_element_with_fallback(driver, slot_element)

    if wait_for_slot_unavailable_popup(driver, max_wait_sec=popup_wait_sec):
        dismiss_slot_unavailable_popup(driver)
        raise Exception(f"Slot {slot_text} is unavailable")


def is_slot_unavailable_popup_visible(driver):
    unavailable_text = driver.find_elements(
        AppiumBy.ANDROID_UIAUTOMATOR,
        'new UiSelector().textContains("slot is not available")'
    )
    got_it_button = driver.find_elements(
        AppiumBy.ANDROID_UIAUTOMATOR,
        'new UiSelector().text("Got it")'
    )
    return bool(unavailable_text) and bool(got_it_button)


def wait_for_slot_unavailable_popup(driver, max_wait_sec=1.2, poll_sec=0.2):
    deadline = time.time() + max_wait_sec
    while time.time() < deadline:
        if is_slot_unavailable_popup_visible(driver):
            return True
        time.sleep(poll_sec)
    return False


def dismiss_slot_unavailable_popup(driver):
    try:
        safe_click(
            driver,
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("Got it")'),
            retries=1,
            timeout=1,
            retry_delay=0,
        )
        print("Dismissed unavailable-slot popup: Got it")
        write_log("slot_popup", "success", details="Clicked Got it")
    except Exception:
        # Popup is not always present; ignore when absent.
        pass


def select_preferred_slot_with_court_fallback(
    driver,
    preferred_slots_by_window,
    preferred_courts,
    min_capacity,
    per_slot_timeout=config.PER_SLOT_TIMEOUT_SEC,
    popup_wait_sec=1.2,
    post_capacity_stabilize_sec=0,
    reselect_slot_window_on_each_court=True,
):
    last_error = None
    empty_state_recheck_used = False

    for slot_window, preferred_slots in preferred_slots_by_window.items():
        slot_window_selected = False
        for court_name in preferred_courts:
            court_attempt_start = time.perf_counter()
            select_court(driver, court_name)
            if reselect_slot_window_on_each_court or not slot_window_selected:
                select_slot_window(driver, slot_window)
                slot_window_selected = True

            if is_no_slots_found_visible(driver):
                still_empty = maybe_recheck_empty_slot_state(
                    driver,
                    slot_window,
                    recheck_sec=config.EMPTY_STATE_RECHECK_SEC,
                    enabled=config.EMPTY_STATE_RECHECK_ENABLED and not empty_state_recheck_used,
                )
                empty_state_recheck_used = True
                if still_empty:
                    last_error = Exception(
                        f"No slots found for window={slot_window}, court={court_name}"
                    )
                    print(f"No slots found: window={slot_window}, court={court_name}")
                    print_timing(
                        f"Combo timing window={slot_window} slot=- court={court_name}",
                        time.perf_counter() - court_attempt_start,
                    )
                    write_log(
                        "select_slot_court",
                        "failure",
                        selected_slot="-",
                        details=f"Window={slot_window} | Court={court_name} | empty_state",
                    )
                    continue

            for slot_text in preferred_slots:
                try:
                    select_slot_with_timeout(
                        driver,
                        slot_text,
                        timeout=per_slot_timeout,
                        popup_wait_sec=popup_wait_sec,
                    )
                    capacity = get_available_capacity(driver)
                    if post_capacity_stabilize_sec > 0:
                        time.sleep(post_capacity_stabilize_sec)

                    if capacity < min_capacity:
                        last_error = Exception(
                            f"Capacity {capacity} is below required minimum {min_capacity}"
                        )
                        print(
                            f"Rejected combo due to capacity: "
                            f"window={slot_window}, slot={slot_text}, court={court_name}, capacity={capacity}"
                        )
                        write_log(
                            "capacity_check",
                            "failure",
                            selected_slot=slot_text,
                            details=(
                                f"Window={slot_window} | Court={court_name} | "
                                f"capacity={capacity} < min={min_capacity}"
                            ),
                        )
                        print_timing(
                            f"Combo timing window={slot_window} slot={slot_text} court={court_name}",
                            time.perf_counter() - court_attempt_start,
                        )
                        write_log(
                            "select_slot_court",
                            "failure",
                            selected_slot=slot_text,
                            details=(
                                f"Window={slot_window} | Court={court_name} | "
                                f"capacity={capacity} < min={min_capacity}"
                            ),
                        )
                        continue

                    print(f"Selected window/slot/court: {slot_window} | {slot_text} | {court_name}")
                    print_timing(
                        f"Combo timing window={slot_window} slot={slot_text} court={court_name}",
                        time.perf_counter() - court_attempt_start,
                    )
                    write_log(
                        "select_slot_court",
                        "success",
                        selected_slot=slot_text,
                        details=f"Window={slot_window} | Court={court_name}",
                    )
                    return slot_text, court_name
                except Exception as exc:
                    last_error = exc
                    print(f"Unavailable combo: window={slot_window}, slot={slot_text}, court={court_name}")
                    print_timing(
                        f"Combo timing window={slot_window} slot={slot_text} court={court_name}",
                        time.perf_counter() - court_attempt_start,
                    )
                    write_log(
                        "select_slot_court",
                        "failure",
                        selected_slot=slot_text,
                        details=f"Window={slot_window} | Court={court_name} | {type(exc).__name__}: {exc}",
                    )

    raise Exception(
        f"No preferred window/slot/court combo found. Mapping={preferred_slots_by_window}, Courts={preferred_courts}"
    ) from last_error


def get_available_capacity(driver):
    capacity_label = wait_present(
        driver,
        (
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().resourceId("com.app.nobrokerhood:id/labelAvailableSlot")'
        )
    )
    capacity_text = capacity_label.text
    match = re.search(r"(\d+)", capacity_text)
    capacity = int(match.group(1)) if match else 0
    print(f"Capacity label: {capacity_text}")
    print(f"Parsed capacity: {capacity}")
    write_log(
        "capacity_check",
        "success",
        details=f"Capacity label evaluated: {capacity_text} | parsed={capacity}",
    )
    return capacity


def select_family_members(driver, members, action_timeout=config.WAIT_SEC):
    wait_click(
        driver,
        (
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().className("android.widget.Button").text("My Family")'
        ),
        timeout=action_timeout,
    )
    print("Clicked: My Family")

    for member in members:
        checkbox_locator = (
            AppiumBy.XPATH,
            "//android.widget.TextView[@resource-id='com.app.nobrokerhood:id/name'"
            f" and @text='{member}']"
            "/following-sibling::android.widget.CheckBox"
            "[@resource-id='com.app.nobrokerhood:id/nameCheckbox']"
        )
        member_checkbox = wait_present(driver, checkbox_locator, timeout=action_timeout)
        is_checked = member_checkbox.get_attribute("checked") == "true"
        if not is_checked:
            click_element_with_fallback(driver, member_checkbox)
            print(f"Checked: {member}")
        else:
            print(f"Already checked: {member}")

    wait_click(
        driver,
        (
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().resourceId("com.app.nobrokerhood:id/tvAddFamilyUsers")'
            '.text("Add")'
        ),
        timeout=action_timeout,
    )
    print("Clicked: Add")


def confirm_booking(driver, member_count, timeout=config.WAIT_SEC):
    button_text = f"Book for {member_count}"
    wait_click(
        driver,
        (
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().resourceId("com.app.nobrokerhood:id/tv_book_button")'
            f'.text("{button_text}")'
        ),
        timeout=timeout,
    )
    print(f"Clicked: {button_text}")


def detect_booking_success(
    driver,
    selected_slot,
    timeout=config.BOOKING_CONFIRM_TIMEOUT_SEC,
    poll_interval=config.BOOKING_CONFIRM_POLL_SEC,
):
    success_phrases = [
        "booking confirmed",
        "reservation successful",
        "confirmed",
    ]
    end_time = time.time() + timeout

    while time.time() < end_time:
        source = driver.page_source.lower()
        if any(phrase in source for phrase in success_phrases):
            print("Booked successfully")
            capture_screenshot(driver, "success", "booking_confirmed")
            write_log(
                "booking_confirmation",
                "success",
                selected_slot=selected_slot,
                details="Confirmed text found",
            )
            return True
        time.sleep(poll_interval)

    print("Booking success message not detected.")
    write_log(
        "booking_confirmation",
        "failure",
        selected_slot=selected_slot,
        details="No confirmation text",
    )
    return False


def build_release_slot_preferences(release_profile):
    return {release_profile["window"]: [release_profile["slot"]]}


def get_next_release_profile(now=None):
    now = now or datetime.now()
    release_profiles = []

    for release_time, release_profile in config.RELEASE_SLOT_MAP.items():
        release_dt = datetime.combine(
            now.date(),
            datetime.strptime(release_time, "%H:%M").time(),
        )
        if release_dt < now:
            release_dt += timedelta(days=1)
        release_profiles.append((release_dt, release_time, release_profile))

    target_dt, release_key, release_profile = min(release_profiles, key=lambda item: item[0])
    return target_dt, release_key, release_profile


def resolve_race_target(now=None):
    now = now or datetime.now()
    test_delay_sec = config.RACE_TEST_TRIGGER_AFTER_SEC

    if test_delay_sec is not None:
        target_dt = now + timedelta(seconds=test_delay_sec)
        return target_dt, f"test+{int(test_delay_sec)}s", config.RACE_TEST_PROFILE

    return get_next_release_profile(now=now)


def wait_for_release_boundary(target_dt, release_key, driver=None):
    initial_remaining_sec = max(0, (target_dt - datetime.now()).total_seconds())
    target_label = target_dt.strftime("%Y-%m-%d %H:%M:%S")
    print(
        f"Race target resolved: {release_key} at {target_label} "
        f"(wait {initial_remaining_sec:.1f}s)"
    )
    write_log(
        "race_wait",
        "success",
        selected_slot="-",
        details=f"release={release_key} target={target_label} wait_sec={initial_remaining_sec:.1f}",
    )

    last_logged_bucket = None
    last_keepalive_at = time.monotonic()
    while True:
        now = datetime.now()
        if now >= target_dt:
            print(f"Race trigger reached: {release_key} at {now.strftime('%Y-%m-%d %H:%M:%S')}")
            return

        remaining_sec = (target_dt - now).total_seconds()
        if remaining_sec <= config.RACE_LAST_MILE_WINDOW_SEC:
            sleep_sec = config.RACE_LAST_MILE_POLL_INTERVAL_SEC
        elif remaining_sec <= config.RACE_FINAL_WINDOW_SEC:
            sleep_sec = config.RACE_FINAL_POLL_INTERVAL_SEC
        else:
            sleep_sec = config.RACE_POLL_INTERVAL_SEC

        if remaining_sec <= config.RACE_FINAL_WINDOW_SEC:
            bucket = int(remaining_sec)
        else:
            bucket = int(remaining_sec // config.RACE_PROGRESS_LOG_INTERVAL_SEC)

        if bucket != last_logged_bucket:
            print(
                f"Polling now={now.strftime('%Y-%m-%d %H:%M:%S')} "
                f"remaining={remaining_sec:.1f}s target={release_key}"
            )
            last_logged_bucket = bucket

        if (
            driver is not None
            and time.monotonic() - last_keepalive_at >= config.RACE_SESSION_KEEPALIVE_INTERVAL_SEC
        ):
            keep_session_alive(driver)
            last_keepalive_at = time.monotonic()

        time.sleep(sleep_sec)


def refresh_tomorrow_and_select_target_slot(
    driver,
    target_day_name,
    hold_day_name,
    release_slot_preferences,
    preferred_courts,
    min_capacity,
):
    deadline = time.time() + config.RACE_REFRESH_RETRY_TIMEOUT_SEC
    last_error = None
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        attempt_start = time.perf_counter()
        try:
            select_day_if_needed(driver, target_day_name)
            selected_slot, selected_court = select_preferred_slot_with_court_fallback(
                driver,
                release_slot_preferences,
                preferred_courts,
                min_capacity=min_capacity,
                per_slot_timeout=config.RACE_SLOT_TIMEOUT_SEC,
                popup_wait_sec=config.RACE_SLOT_UNAVAILABLE_POPUP_WAIT_SEC,
                post_capacity_stabilize_sec=config.RACE_POST_CAPACITY_STABILIZE_SEC,
                reselect_slot_window_on_each_court=True,
            )
            print_timing(
                f"Refresh attempt {attempt} to target day + slot selection",
                time.perf_counter() - attempt_start,
            )
            return selected_slot, selected_court
        except Exception as exc:
            last_error = exc
            print_timing(
                f"Refresh attempt {attempt} to target day + slot selection",
                time.perf_counter() - attempt_start,
            )
            try:
                select_day_if_needed(driver, hold_day_name)
                select_day_if_needed(driver, target_day_name)
            except Exception:
                pass
            time.sleep(config.RACE_FINAL_POLL_INTERVAL_SEC)

    raise Exception(
        f"Target slot did not become bookable before timeout. Mapping={release_slot_preferences}"
    ) from last_error


def run_booking_flow_from_booking_screen(
    driver,
    day_name,
    preferred_courts,
    preferred_slots_by_window,
    family_members,
    min_capacity,
    post_capacity_stabilize_sec,
):
    select_day(driver, day_name)
    selected_slot, selected_court = select_preferred_slot_with_court_fallback(
        driver,
        preferred_slots_by_window,
        preferred_courts,
        min_capacity=min_capacity,
        post_capacity_stabilize_sec=post_capacity_stabilize_sec,
    )

    select_family_members(driver, family_members)
    # confirm_booking(driver, len(family_members))

    if not detect_booking_success(driver, selected_slot=selected_slot):
        raise Exception("Booking confirmation message not detected.")

    write_log(
        "run_booking_flow",
        "success",
        selected_slot=selected_slot,
        details=f"Booked {selected_court}",
    )
    return selected_slot


def run_race():
    driver = None
    selected_slot = "-"
    start_time = time.perf_counter()
    booking_page_ready_time = None
    try:
        target_dt, release_key, release_profile = resolve_race_target()
        release_slot_preferences = build_release_slot_preferences(release_profile)

        driver = open_app()
        ensure_app_in_foreground(driver)
        enforce_session_guard(driver)
        open_booking_screen(driver, config.SPORT)
        select_day_if_needed(driver, config.RACE_DAY_HOLD)
        booking_page_ready_time = time.perf_counter()
        booking_page_ready_elapsed_sec = booking_page_ready_time - start_time
        print(
            "Booking page ready in "
            f"{booking_page_ready_elapsed_sec:.2f}s "
            f"[{format_elapsed_sec(booking_page_ready_elapsed_sec)}]"
        )

        write_log(
            "race",
            "success",
            selected_slot="-",
            details=(
                f"Prepared booking page for release={release_key} "
                f"target_slot={release_profile['slot']} hold_day={config.RACE_DAY_HOLD}"
            ),
        )

        wait_for_release_boundary(target_dt, release_key, driver=driver)
        trigger_reached_time = time.perf_counter()
        print_timing(
            "Time from booking page ready to trigger",
            trigger_reached_time - booking_page_ready_time,
        )

        slot_selection_start = time.perf_counter()
        selected_slot, selected_court = refresh_tomorrow_and_select_target_slot(
            driver=driver,
            target_day_name=config.DAY,
            hold_day_name=config.RACE_DAY_HOLD,
            release_slot_preferences=release_slot_preferences,
            preferred_courts=config.PREFERRED_COURTS,
            min_capacity=config.MIN_CAPACITY,
        )
        print_timing(
            "Time from trigger to slot selection",
            time.perf_counter() - slot_selection_start,
        )

        family_selection_start = time.perf_counter()
        select_family_members(
            driver,
            config.FAMILY_MEMBERS,
            action_timeout=config.RACE_FAMILY_ACTION_TIMEOUT_SEC,
        )
        print_timing(
            "Family selection",
            time.perf_counter() - family_selection_start,
        )
        booking_submission_start = time.perf_counter()
        # confirm_booking(
        #     driver,
        #     len(config.FAMILY_MEMBERS),
        #     timeout=config.RACE_CONFIRM_BUTTON_TIMEOUT_SEC,
        # )
        print_timing(
            "Booking submission",
            time.perf_counter() - booking_submission_start,
        )

        booking_after_page_sec = time.perf_counter() - booking_page_ready_time
        print_timing("Time from booking page ready to booking submission", booking_after_page_sec)

        if config.RACE_REQUIRE_CONFIRMATION:
            booking_confirmation_start = time.perf_counter()
            if not detect_booking_success(driver, selected_slot=selected_slot):
                raise Exception("Booking confirmation message not detected.")
            print_timing(
                "Booking confirmation detection",
                time.perf_counter() - booking_confirmation_start,
            )

        elapsed_sec = time.perf_counter() - start_time
        booking_after_page_sec = elapsed_sec - booking_page_ready_elapsed_sec
        if config.RACE_REQUIRE_CONFIRMATION:
            print_timing("Time from booking page ready to booking outcome", booking_after_page_sec)
        write_log(
            "timing",
            "success",
            selected_slot=selected_slot,
            details=f"Elapsed seconds: {elapsed_sec:.2f}",
        )
        write_log(
            "main",
            "success",
            selected_slot=selected_slot,
            details=(
                f"Race flow completed in {elapsed_sec:.2f}s | "
                f"release={release_key} | court={selected_court} | "
                f"confirmation_required={config.RACE_REQUIRE_CONFIRMATION}"
            ),
        )
        return True, (
            f"Booked successfully. Release: {release_key}. "
            f"Slot: {selected_slot}. Time: {elapsed_sec:.2f}s"
        )
    except Exception as exc:
        elapsed_sec = time.perf_counter() - start_time
        if booking_page_ready_time is not None:
            booking_after_page_sec = elapsed_sec - (booking_page_ready_time - start_time)
            print_timing("Time from booking page ready to booking outcome", booking_after_page_sec)
        if driver is not None:
            capture_screenshot(driver, "failure", "race_flow_exception")
        write_log(
            "timing",
            "failure",
            selected_slot=selected_slot,
            details=f"Elapsed seconds: {elapsed_sec:.2f}",
        )
        write_log(
            "main",
            "failure",
            selected_slot=selected_slot,
            details=f"{type(exc).__name__}: {exc} | after {elapsed_sec:.2f}s",
        )
        return False, f"{exc} (after {elapsed_sec:.2f}s)"
    finally:
        if driver is not None:
            close_app(driver)
