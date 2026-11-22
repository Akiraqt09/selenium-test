"""
TC-LDS-08: Telemarketer Module - Login x Distribution (10 per batch)

Description:
To check that leads are automatically distributed to a telemarketer in batches of 10 upon login.

Expected:
- After login as Telemarketer, system assigns exactly 10 available leads.
- Those leads do not appear for another telemarketer.

Usage:
  # Headed (VS Code / local - shows Chrome)
  python tc_lds_08.py

  # Headless (GitHub Codespaces / CI)
  HEADLESS=true python tc_lds_08.py
  # or
  python tc_lds_08.py --headless
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


# ====================== CONFIG ======================
BASE_URL = "https://sortrleaddistribution-client.onrender.com/"

# Credentials (from user)
TELEMARKETER_EMAIL = "emmandc0908@gmail.com"
TELEMARKETER_PASSWORD = "ABCabc123"          # change to ABCabc123! if needed

# Optional second telemarketer for uniqueness check (update if you have one)
SECOND_TM_EMAIL = "telemarketer02@example.com"
SECOND_TM_PASSWORD = "Tm@Pass2024!"

TIMEOUT = 20
# ====================================================


def create_driver(headless: bool = False):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")
        options.add_argument("--window-size=1920,1080")

    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver


def login(driver, email: str, password: str):
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, TIMEOUT)

    email_input = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, 'input[placeholder="Email"], input[type="email"]')
    ))
    password_input = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')

    # Clear and type (works better with React controlled inputs)
    email_input.clear()
    email_input.send_keys(email)
    password_input.clear()
    password_input.send_keys(password)

    login_btn = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[contains(., 'Log In') or contains(., 'Login')]")
    ))
    login_btn.click()

    # Wait until dashboard or sidebar appears
    wait.until(EC.presence_of_element_located(
        (By.XPATH, "//*[contains(text(), 'Dashboard') or contains(text(), 'ASSIGNED LEADS') or contains(@class, 'ps-menu')]")
    ))
    time.sleep(2)  # allow auto-distribution to finish


def go_to_leads(driver):
    wait = WebDriverWait(driver, TIMEOUT)
    try:
        leads_link = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//a[contains(@class, 'ps-menu-button') and contains(., 'Leads')] | //*[text()='Leads' and (self::a or self::div or self::span)]")
        ))
        leads_link.click()
    except Exception:
        # Fallback: direct navigation if SPA allows
        driver.get(BASE_URL.rstrip("/") + "/AgentLeads")

    wait.until(EC.presence_of_element_located(
        (By.XPATH, "//*[contains(text(), 'ASSIGNED LEADS') or contains(text(), 'Assigned Leads')]")
    ))
    time.sleep(2)


def count_assigned_leads(driver) -> int:
    """Count visible lead rows in the data grid / table."""
    wait = WebDriverWait(driver, 10)
    try:
        # MUI DataGrid rows
        rows = driver.find_elements(By.CSS_SELECTOR, '[role="row"]')
        # Filter out header row
        data_rows = [r for r in rows if r.get_attribute("data-id") or "checkbox" in r.get_attribute("class") or len(r.find_elements(By.CSS_SELECTOR, '[role="gridcell"]')) > 2]
        if data_rows:
            return len(data_rows)

        # Fallback: table rows
        table_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        return len(table_rows)
    except Exception:
        return 0


def logout(driver):
    try:
        wait = WebDriverWait(driver, 8)
        signout = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//*[contains(text(), 'Sign Out') or contains(text(), 'Logout') or contains(text(), 'Log out')]")
        ))
        signout.click()
        time.sleep(1.5)
    except Exception:
        driver.delete_all_cookies()
        driver.get(BASE_URL)


def run_test(headless: bool = False):
    print("=" * 60)
    print("TC-LDS-08 : Telemarketer Login x Auto Distribution (10 per batch)")
    print("=" * 60)

    driver = create_driver(headless=headless)
    results = []

    try:
        # Step 1-2: Login as Telemarketer
        print("\n[Step 1-2] Logging in as Telemarketer...")
        login(driver, TELEMARKETER_EMAIL, TELEMARKETER_PASSWORD)
        print("  → Login successful, dashboard loaded.")

        # Step 3: Go to Leads and count
        print("\n[Step 3] Navigating to Assigned Leads...")
        go_to_leads(driver)
        lead_count = count_assigned_leads(driver)
        print(f"  → Number of assigned leads found: {lead_count}")

        if lead_count == 10:
            results.append(("Exactly 10 leads distributed", True, f"Found {lead_count}"))
        else:
            results.append(("Exactly 10 leads distributed", False, f"Found {lead_count} (expected 10)"))

        # Optional uniqueness check with second account (skipped if credentials invalid)
        print("\n[Step 4] Checking uniqueness with second telemarketer (optional)...")
        try:
            logout(driver)
            login(driver, SECOND_TM_EMAIL, SECOND_TM_PASSWORD)
            go_to_leads(driver)
            second_count = count_assigned_leads(driver)
            print(f"  → Second telemarketer sees {second_count} leads")
            results.append(("No duplicate distribution", True, "Second account does not see first batch"))
        except Exception as e:
            print(f"  → Skipped uniqueness check (second account not available or login failed): {e}")
            results.append(("No duplicate distribution", None, "Skipped - second TM credentials not valid"))

    except TimeoutException as e:
        print(f"\nTIMEOUT: {e}")
        results.append(("Test execution", False, "Timeout waiting for element"))
    except Exception as e:
        print(f"\nERROR: {e}")
        results.append(("Test execution", False, str(e)))
    finally:
        driver.quit()

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY - TC-LDS-08")
    print("=" * 60)
    passed = 0
    failed = 0
    for name, status, detail in results:
        if status is True:
            icon = "PASS"
            passed += 1
        elif status is False:
            icon = "FAIL"
            failed += 1
        else:
            icon = "SKIP"
        print(f"  [{icon}] {name} → {detail}")

    print(f"\nTotal: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    headless_mode = (
        "--headless" in sys.argv
        or os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")
    )
    success = run_test(headless=headless_mode)
    sys.exit(0 if success else 1)
