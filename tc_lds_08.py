"""
TC-LDS-08 - Verify automatic distribution of 10 leads to a telemarketer.

READ-ONLY:
- Does not create, edit, delete, assign, or distribute leads.
- Does not log out and switch to a second telemarketer account.
- Checks the current telemarketer's Assigned Leads list for exactly 10 rows.
- Checks for exact duplicate visible row records when the page exposes row cells.

Requirements:
    python -m pip install -U selenium python-dotenv

Credentials:
    Enter TELEMARKETER_EMAIL and TELEMARKETER_PASSWORD in the configuration
    section near the top of this single Python file.
"""

import os
import re
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================================================
# ALL TEST CASE SETTINGS AND TEST ACCOUNT CREDENTIALS
# Edit these values directly in THIS file. No .env is required.
# Do not commit real passwords to a public GitHub repository.
# ============================================================

CASE_ID = "TC-LDS-08"

BASE_URL = "https://sortrleaddistribution-client.onrender.com/"

# Enter the dedicated TELEMARKETER test account credentials here.
TELEMARKETER_EMAIL = "PUT_TELEMARKETER_TEST_EMAIL_HERE"
TELEMARKETER_PASSWORD = "PUT_TELEMARKETER_TEST_PASSWORD_HERE"

EXPECTED_LEADS = 10
WAIT_SECONDS = 30

# Browser settings. Leave CHROME_BINARY as None to let Selenium Manager
# locate Chrome automatically. If needed, set e.g. "/usr/bin/google-chrome".
CHROME_BINARY = None
HEADLESS = True

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


# ============================================================
# TEST UTILITIES
# ============================================================

class TestFailure(Exception):
    pass


def get_credentials():
    """Read credentials without hardcoding or printing the password."""
    email = TELEMARKETER_EMAIL.strip()
    password = TELEMARKETER_PASSWORD

    if (
        not email
        or not password
        or email == "PUT_TELEMARKETER_TEST_EMAIL_HERE"
        or password == "PUT_TELEMARKETER_TEST_PASSWORD_HERE"
    ):
        raise TestFailure(
            "Set TELEMARKETER_EMAIL and TELEMARKETER_PASSWORD in the "
            "configuration section at the top of this Python file."
        )
    return email, password


def make_driver():
    options = webdriver.ChromeOptions()

    # Codespaces normally has no desktop display.
    if HEADLESS:
        options.add_argument("--headless=new")

    # Required/recommended for container environments such as Codespaces.
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1600,1100")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    if CHROME_BINARY:
        options.binary_location = CHROME_BINARY

    # Selenium Manager (included with Selenium 4.6+) resolves the driver.
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(0)

    print(f"[INFO] Browser: {driver.capabilities.get('browserName')}")
    print(f"[INFO] Browser version: {driver.capabilities.get('browserVersion')}")
    print(f"[INFO] Browser mode: {'HEADLESS' if HEADLESS else 'HEADED'}")
    return driver


def save_screenshot(driver, label):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = re.sub(r"[^A-Za-z0-9_-]+", "_", label)
    path = SCREENSHOT_DIR / f"{timestamp}_{safe_label}.png"
    try:
        driver.save_screenshot(str(path))
        print(f"[EVIDENCE] Screenshot saved: {path}")
    except WebDriverException as exc:
        print(f"[WARNING] Screenshot could not be saved: {exc}")


def visible_body_text(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except WebDriverException:
        return ""


def find_visible_input(driver, selectors):
    for selector in selectors:
        for element in driver.find_elements(By.CSS_SELECTOR, selector):
            try:
                if element.is_displayed() and element.is_enabled():
                    return element
            except StaleElementReferenceException:
                continue
    return None


def click_element(driver, element):
    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'});", element
    )
    try:
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", element)


def click_login_button(driver):
    candidates = driver.find_elements(
        By.XPATH,
        "//button[normalize-space()='Log In' or normalize-space()='Login' "
        "or normalize-space()='Sign In']"
    )
    for element in candidates:
        if element.is_displayed() and element.is_enabled():
            click_element(driver, element)
            return
    raise TestFailure("Could not locate the Log In button.")


def login_telemarketer(driver, email, password):
    print("[STEP] Opening the application login page...")
    driver.get(BASE_URL)

    WebDriverWait(driver, WAIT_SECONDS).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

    email_field = find_visible_input(driver, [
        "input[type='email']",
        "input[name='email']",
        "input[placeholder*='Email' i]",
        "input[id*='email' i]",
    ])
    password_field = find_visible_input(driver, [
        "input[type='password']",
        "input[name='password']",
        "input[placeholder*='Password' i]",
        "input[id*='password' i]",
    ])

    if not email_field or not password_field:
        raise TestFailure(
            "Login form fields were not found. "
            "The website layout or login page may have changed."
        )

    email_field.clear()
    email_field.send_keys(email)
    password_field.clear()
    password_field.send_keys(password)

    print("[STEP] Submitting the configured telemarketer login...")
    click_login_button(driver)

    WebDriverWait(driver, WAIT_SECONDS).until(
        lambda d: (
            "login" not in d.current_url.lower()
            or any(word in visible_body_text(d).lower()
                   for word in ("invalid", "incorrect", "error"))
        )
    )
    time.sleep(1.5)

    body = visible_body_text(driver).lower()
    rejected_messages = (
        "invalid credentials",
        "incorrect password",
        "account not found",
        "invalid email",
        "wrong password",
    )
    if any(message in body for message in rejected_messages):
        raise TestFailure(
            "The telemarketer login was rejected. "
            "Check that the configured test account is valid."
        )

    print("[PASS] Login form submitted; application dashboard/page loaded.")


def open_assigned_leads(driver):
    print("[STEP] Opening Assigned Leads...")
    labels = (
        "Assigned Leads",
        "Assigned Lead",
        "My Leads",
    )

    for label in labels:
        xpath = (
            "//*[self::a or self::button or @role='button' or "
            "self::li][normalize-space(.)="
            + xpath_string(label)
            + "]"
        )
        for element in driver.find_elements(By.XPATH, xpath):
            try:
                if element.is_displayed() and element.is_enabled():
                    click_element(driver, element)
                    time.sleep(1.5)
                    print(f"[INFO] Opened navigation item: {label}")
                    return
            except StaleElementReferenceException:
                continue

    # If the current page already shows a likely assigned-leads table/grid,
    # do not click a guessed menu item.
    if get_visible_data_rows(driver):
        print("[INFO] A visible data table/grid is already present.")
        return

    raise TestFailure(
        "Could not find the Assigned Leads navigation item or a visible "
        "assigned-leads table. Inspect the saved screenshot."
    )


def xpath_string(value):
    if "'" not in value:
        return "'" + value + "'"
    if '"' not in value:
        return '"' + value + '"'
    parts = value.split("'")
    return "concat(" + ", \"'\", ".join("'" + p + "'" for p in parts) + ")"


def get_visible_data_rows(driver):
    """
    Read visible data rows from standard HTML tables or ARIA/MUI grids.
    Header rows are excluded. Duplicate selectors are de-duplicated.
    """
    found = []
    seen_ids = set()

    selectors = [
        "table tbody tr",
        "[role='grid'] [role='row']",
        ".MuiDataGrid-virtualScrollerRenderZone [role='row']",
        ".MuiDataGrid-row",
    ]

    for selector in selectors:
        for row in driver.find_elements(By.CSS_SELECTOR, selector):
            try:
                if not row.is_displayed():
                    continue
                text = row.text.strip()
                if not text:
                    continue

                # Exclude header rows and column-label-only rows.
                role = (row.get_attribute("role") or "").lower()
                classes = (row.get_attribute("class") or "").lower()
                if "header" in classes or "columnheader" in role:
                    continue

                cells = row.find_elements(
                    By.CSS_SELECTOR,
                    "td, [role='gridcell'], .MuiDataGrid-cell"
                )
                if not cells and row.find_elements(
                    By.CSS_SELECTOR, "th, [role='columnheader']"
                ):
                    continue

                identity = row.id
                if identity not in seen_ids:
                    seen_ids.add(identity)
                    found.append(row)
            except StaleElementReferenceException:
                continue

    return found


def row_signature(row):
    """Build a normalized signature from the visible data cells."""
    cells = row.find_elements(
        By.CSS_SELECTOR,
        "td, [role='gridcell'], .MuiDataGrid-cell"
    )
    values = []
    for cell in cells:
        try:
            value = " ".join(cell.text.split())
            if value:
                values.append(value.casefold())
        except StaleElementReferenceException:
            continue

    if values:
        return tuple(values)

    return tuple(" ".join(row.text.split()).casefold().split("|"))


def inspect_assigned_leads(driver):
    print("[STEP] Waiting for the Assigned Leads list to render...")

    WebDriverWait(driver, WAIT_SECONDS).until(
        lambda d: (
            len(get_visible_data_rows(d)) > 0
            or "no leads" in visible_body_text(d).lower()
            or "no rows" in visible_body_text(d).lower()
        )
    )

    time.sleep(1)
    rows = get_visible_data_rows(driver)
    count = len(rows)

    print(f"[OBSERVED] Visible assigned lead rows: {count}")
    save_screenshot(driver, "TC_LDS_08_assigned_leads")

    if count == 0:
        body = visible_body_text(driver).lower()
        if "no leads" in body or "no rows" in body:
            raise TestFailure(
                "The Assigned Leads page is empty; expected 10 assigned leads."
            )
        raise TestFailure(
            "No visible lead rows were detected. The page may use a different "
            "table/grid layout; inspect the screenshot."
        )

    if count != EXPECTED_LEADS:
        raise TestFailure(
            f"Expected exactly {EXPECTED_LEADS} assigned leads, "
            f"but observed {count}."
        )

    print(f"[PASS] Exactly {EXPECTED_LEADS} assigned lead rows are visible.")

    # Exact duplicate check across all visible cell values.
    signatures = []
    for row in rows:
        try:
            signature = row_signature(row)
            if signature:
                signatures.append(signature)
        except StaleElementReferenceException:
            raise TestFailure(
                "The lead list changed while it was being inspected. "
                "Refresh and rerun the test."
            )

    duplicate_signatures = sorted({
        sig for sig in signatures if signatures.count(sig) > 1
    })

    if duplicate_signatures:
        print(
            f"[WARNING] Found {len(duplicate_signatures)} exact duplicate "
            "visible row signature(s)."
        )
        for index, signature in enumerate(duplicate_signatures, start=1):
            print(f"  Duplicate {index}: {' | '.join(signature)}")
        raise TestFailure(
            "The Assigned Leads list contains exact duplicate visible rows."
        )

    print("[PASS] No exact duplicate visible lead rows were detected.")
    print(
        "[NOTE] This duplicate check compares the complete visible row values; "
        "it cannot detect the same person represented by different names or "
        "different visible details."
    )


# ============================================================
# TEST EXECUTION
# ============================================================

def main():
    driver = None
    status = "ERROR"

    print()
    print("=" * 62)
    print(f"{CASE_ID}: VERIFY AUTOMATIC DISTRIBUTION OF 10 LEADS")
    print("=" * 62)
    print("[INFO] Test type: READ-ONLY")
    print("[INFO] Expected assigned leads: 10")
    print("[INFO] Second telemarketer login: SKIPPED")
    print("[INFO] No lead records will be modified.")
    print()

    try:
        email, password = get_credentials()
        driver = make_driver()

        login_telemarketer(driver, email, password)
        save_screenshot(driver, "TC_LDS_08_after_login")

        open_assigned_leads(driver)
        inspect_assigned_leads(driver)

        status = "PASS"

    except TestFailure as exc:
        status = "FAIL"
        print(f"[FAIL] {exc}")

    except TimeoutException as exc:
        status = "FAIL"
        print(f"[FAIL] Timed out waiting for a page element: {exc}")

    except WebDriverException as exc:
        status = "ERROR"
        print(f"[ERROR] Selenium/browser error: {type(exc).__name__}: {exc}")
        print(
            "[HINT] Check Chrome installation, Chrome startup, network access, "
            "and Selenium Manager/driver compatibility."
        )

    except KeyboardInterrupt:
        status = "ABORTED"
        print("[ABORTED] Test stopped by user.")

    except Exception as exc:
        status = "ERROR"
        print(f"[ERROR] Unexpected {type(exc).__name__}: {exc}")
        traceback.print_exc()

    finally:
        if driver:
            try:
                save_screenshot(driver, f"TC_LDS_08_final_{status}")
            except Exception:
                pass
            try:
                driver.quit()
            except Exception:
                pass

        print()
        print("=" * 62)
        print(f"{CASE_ID} FINAL RESULT: {status}")
        print("=" * 62)
        print(f"Evidence folder: {SCREENSHOT_DIR.resolve()}")
        print("No second telemarketer account was used.")
        print("No lead data was changed.")
        print("=" * 62)

    if status == "PASS":
        return 0
    if status == "ABORTED":
        return 130
    return 1


if __name__ == "__main__":
    sys.exit(main())
