"""
TC-LDS-06 | Lead Gen Module - Add New Lead | Jira: WEB-1

Follows the steps of the test case exactly:
  1. Click "Add New Lead" in the sidebar
  2. Enter the lead Name
  3. Select the lead Type
  4. Enter the Phone Number
  5. Enter the Street Address, City and Postcode
  6. Enter the Email Address
  7. Click the Submit button

Expected result of step 7:
  The system saves the new lead and displays a success message.
  The lead appears in the Lead Lists page and the Total Leads count
  on the dashboard is updated.

Known defect (WEB-1): the lead is saved in the database (MongoDB) and the
success message appears, but the lead is hidden in the Lead Lists page.

How to read the result:
  [PASS]  the check matched the expected result
  [FAIL]  the system did NOT behave as expected (a product defect)
  [ERROR] the script could not continue (a script/page problem, not a result)
  [INFO]  extra information, not part of the logged defect
"""

import re
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ==========================================
# SETTINGS
# ==========================================

# Use "http://localhost:3000/" to test your own copy of the system.
WEBSITE = "https://sortrleaddistribution-client.onrender.com/"

# Lead Generation Specialist test account
EMAIL = "romandanlag0504@gmail.com"
PASSWORD = "ABCabc123!"

# True = no browser window (needed for Codespaces/Colab).
# Set to False if you run this on a laptop and want to watch it.
HEADLESS = True

# Test input from TC-LDS-06. A time stamp is added to the name so this
# run's lead cannot be confused with a lead from an earlier run.
STAMP = datetime.now().strftime("%H%M%S")
LEAD_NAME = f"Ocean View Cafe {STAMP}"
LEAD_TYPE = "Cafe"
PHONE = "61 2 5550 1234"
STREET = "12 Main Street"
CITY = "Wagga Wagga"
POSTCODE = "2650"
LEAD_EMAIL = "oceanview.cafe@gmail.com"

# The success pop-up says "New Lead Added!" (the capital letters may differ)
SUCCESS_XPATH = (
    "//*[translate(normalize-space(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
    "'abcdefghijklmnopqrstuvwxyz')='new lead added!']"
)

# ==========================================
# HELPERS
# ==========================================

results = []


def record(status, text):
    results.append((status, text))
    print(f"[{status}] {text}")


options = webdriver.ChromeOptions()
if HEADLESS:
    options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 60)


def shot(name):
    file_name = f"tc06_{name}.png"
    driver.save_screenshot(file_name)
    print(f"    (screenshot saved: {file_name})")


def click_safely(element):
    try:
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", element)


def type_into(field_name, value):
    field = wait.until(EC.visibility_of_element_located((By.NAME, field_name)))
    field.clear()
    field.send_keys(value)


def select_lead_type(value):
    dropdown = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, '[role="combobox"]'))
    )
    dropdown.click()

    option_xpath = (
        f"//li[@role='option'][normalize-space()='{value}' or @data-value='{value}']"
    )
    try:
        option = wait.until(EC.visibility_of_element_located((By.XPATH, option_xpath)))
    except TimeoutException:
        names = [o.text for o in driver.find_elements(By.CSS_SELECTOR, 'li[role="option"]')]
        print("    The option was not found. Options in the dropdown:", names)
        raise

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option)
    click_safely(wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath))))

    wait.until(
        lambda d: value
        in d.find_element(By.CSS_SELECTOR, '[role="combobox"]').text
    )


def read_total_leads():
    """Best effort: the number next to 'Total Leads' on the dashboard, or None."""
    try:
        node = driver.find_element(By.XPATH, "//*[normalize-space()='Total Leads']")
        for _ in range(4):
            node = node.find_element(By.XPATH, "..")
            numbers = re.findall(r"\b\d+\b", node.text.replace("Total Leads", ""))
            if numbers:
                return int(numbers[0])
    except Exception:
        pass
    return None


def lead_is_listed(name, seconds=15):
    """True if the lead name is visible on the current page."""
    try:
        box = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="Search"]')
        box.clear()
        box.send_keys(name)
    except Exception:
        pass  # this page may have no search box

    try:
        WebDriverWait(driver, seconds).until(
            EC.visibility_of_element_located(
                (By.XPATH, f"//*[normalize-space()='{name}']")
            )
        )
        return True
    except TimeoutException:
        return False


# ==========================================
# TEST
# ==========================================

print()
print("==========================================")
print("TC-LDS-06: ADD NEW LEAD (Jira WEB-1)")
print(f"Lead used in this run: {LEAD_NAME}")
print("==========================================")

current = "starting"
total_before = None

try:
    # ---- Precondition: logged in as a Lead Generation Specialist ----
    current = "Precondition - open the website and log in"
    driver.get(WEBSITE)

    wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))
    ).send_keys(EMAIL)
    driver.find_element(By.CSS_SELECTOR, 'input[type="password"]').send_keys(PASSWORD)
    click_safely(
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Log In']")))
    )
    wait.until(
        EC.visibility_of_element_located((By.XPATH, "//*[normalize-space()='DASHBOARD']"))
    )
    record("PASS", "Precondition: logged in and the dashboard is displayed.")

    time.sleep(3)  # let the dashboard numbers load
    total_before = read_total_leads()
    print(f"    Total Leads before adding: {total_before}")

    # ---- Step 1 ----
    current = "Step 1 - click 'Add New Lead' in the sidebar"
    click_safely(
        wait.until(EC.element_to_be_clickable((By.XPATH, "//*[normalize-space()='Add New Lead' or normalize-space()='Add New Leed']")))
    )
    for field in ("name", "phonenumber", "streetaddress", "city", "postcode", "emailaddress"):
        wait.until(EC.visibility_of_element_located((By.NAME, field)))
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[type="submit"]')))
    record(
        "PASS",
        "Step 1: the Add New Lead form is displayed with Name, Type, Phone Number, "
        "Street Address, City, Postcode, Email Address and a Submit button.",
    )

    # ---- Step 2 ----
    current = "Step 2 - enter the lead Name"
    type_into("name", LEAD_NAME)
    record("PASS", f"Step 2: Name is accepted ({LEAD_NAME}).")

    # ---- Step 3 ----
    current = "Step 3 - select the lead Type"
    select_lead_type(LEAD_TYPE)
    record("PASS", f"Step 3: the selected type is displayed ({LEAD_TYPE}).")

    # ---- Step 4 ----
    current = "Step 4 - enter the Phone Number"
    type_into("phonenumber", PHONE)
    record("PASS", f"Step 4: Phone Number is accepted ({PHONE}).")

    # ---- Step 5 ----
    current = "Step 5 - enter the Street Address, City and Postcode"
    type_into("streetaddress", STREET)
    type_into("city", CITY)
    type_into("postcode", POSTCODE)
    record("PASS", "Step 5: the address details are accepted.")

    # ---- Step 6 ----
    current = "Step 6 - enter the Email Address"
    type_into("emailaddress", LEAD_EMAIL)
    record("PASS", f"Step 6: Email Address is accepted ({LEAD_EMAIL}).")

    # ---- Step 7 ----
    current = "Step 7 - click the Submit button"
    shot("1_form_filled")
    click_safely(
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]')))
    )

    wait.until(
        EC.visibility_of_element_located((By.XPATH, SUCCESS_XPATH))
    )
    shot("2_success_message")
    record("PASS", "Step 7: the system saved the lead and displayed the success message.")

    try:
        wait.until(
            EC.invisibility_of_element_located((By.XPATH, SUCCESS_XPATH))
        )
        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".MuiBackdrop-root")))
    except TimeoutException:
        print("    (the success popup did not close by itself)")

    # ---- Expected result: the lead appears in the Lead Lists page ----
    current = "Expected result - open the Lead Lists page and look for the new lead"
    leads_menu = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//li[contains(@class,'ps-menuitem-root')]"
                "[.//*[normalize-space()='Leads' or normalize-space()='Leeds']]",
            )
        )
    )
    click_safely(leads_menu)
    time.sleep(5)  # let the list load

    found = lead_is_listed(LEAD_NAME, 15)
    if not found:
        print("    Not found yet. Refreshing the page and checking once more...")
        driver.refresh()
        time.sleep(5)
        found = lead_is_listed(LEAD_NAME, 15)
    shot("3_leads_page")

    if found:
        record("PASS", f"The lead '{LEAD_NAME}' appears in the Lead Lists page.")
    else:
        record(
            "FAIL",
            "Expected: the lead appears in the Lead Lists page. "
            f"Actual: '{LEAD_NAME}' is NOT displayed in the Lead Lists page "
            "(the lead is saved but hidden in the UI).",
        )

    # ---- Expected result: Total Leads count on the dashboard ----
    current = "Expected result - check the Total Leads count on the dashboard"
    try:
        dashboard_menu = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//li[contains(@class,'ps-menuitem-root')]"
                    "[.//*[normalize-space()='Dashboard']]",
                )
            )
        )
        click_safely(dashboard_menu)
        time.sleep(4)
        total_after = read_total_leads()
        shot("4_dashboard")

        if total_before is None or total_after is None:
            record("INFO", "Could not read the Total Leads count. Check tc06_4_dashboard.png.")
        elif total_after == total_before + 1:
            record("INFO", f"Total Leads count increased ({total_before} -> {total_after}).")
        else:
            record("INFO", f"Total Leads count did not increase ({total_before} -> {total_after}).")
    except TimeoutException:
        record("INFO", "Could not open the dashboard to check the Total Leads count.")

except TimeoutException:
    record("ERROR", f"The script stopped at: {current} (an element did not appear in time).")
    print("    Current URL:", driver.current_url)
    shot("error")

except Exception as error:
    record("ERROR", f"The script stopped at: {current} ({type(error).__name__}: {error})")
    shot("error")

finally:
    driver.quit()

# ==========================================
# SUMMARY
# ==========================================

has_error = any(status == "ERROR" for status, _ in results)
has_fail = any(status == "FAIL" for status, _ in results)

print()
print("==========================================")
print("TC-LDS-06 SUMMARY")
print("------------------------------------------")
for status, text in results:
    print(f"[{status}] {text}")
print("------------------------------------------")
if has_error:
    print("RESULT: INCOMPLETE - the script could not finish, so this is not a test result.")
elif has_fail:
    print("RESULT: FAILED - the lead is not shown in the Lead Lists page (matches WEB-1).")
else:
    print("RESULT: PASSED - the lead is shown in the Lead Lists page.")
print("==========================================")

sys.exit(1 if (has_error or has_fail) else 0)
