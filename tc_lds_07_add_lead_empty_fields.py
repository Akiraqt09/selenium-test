"""
TC-LDS-07 | Lead Gen Module - Add Lead with Empty Required Field | Jira: WEB-2

The system must NOT save a new lead when a required field is left empty.

For each step the script fills the Add New Lead form with valid data, leaves
ONE field empty (the last step leaves ALL fields empty), then clicks Submit:

  system blocks the lead (no success message)  -> [PASS]
  system saves the lead ("New lead added!")    -> [FAIL]

Steps (same as the test case in the spreadsheet):
  2. Name empty          6. City empty
  3. Type not selected   7. Postcode empty
  4. Phone Number empty  8. Email Address empty
  5. Street Address empty  9. All fields empty

Note: because of defect WEB-1 the Lead Lists page hides new leads, so that
page cannot be used to check. The success message is used instead.

Any lead saved by mistake is a REAL record. Its name contains a time stamp,
so you can find it and delete it afterwards. The summary lists them.

  [PASS]  the system blocked the empty field (expected)
  [FAIL]  the system saved the lead (a product defect)
  [ERROR] the script could not continue (a script/page problem, not a result)
"""

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

WEBSITE = "https://sortrleaddistribution-client.onrender.com/"

# Lead Generation Specialist test account
EMAIL = "romandanlag0504@gmail.com"
PASSWORD = "ABCabc123!"

# True = no browser window (needed for Codespaces/Colab).
# Set to False if you run this on a laptop and want to watch it.
HEADLESS = True

STAMP = datetime.now().strftime("%H%M%S")

# Valid data from TC-LDS-07 (one field is emptied in each step)
FULL = {
    "name": "Ocean View Cafe",
    "type": "Cafe",
    "phonenumber": "61 2 5550 1234",
    "streetaddress": "12 Main Street",
    "city": "Wagga Wagga",
    "postcode": "2650",
    "emailaddress": "oceanview.cafe@example.com",
}
TEXT_FIELDS = ("phonenumber", "streetaddress", "city", "postcode", "emailaddress")

STEPS = [
    (2, "Name", ["name"]),
    (3, "Type", ["type"]),
    (4, "Phone Number", ["phonenumber"]),
    (5, "Street Address", ["streetaddress"]),
    (6, "City", ["city"]),
    (7, "Postcode", ["postcode"]),
    (8, "Email Address", ["emailaddress"]),
    (9, "ALL fields", list(FULL.keys())),
]

DASHBOARD_MENU = (
    "//li[contains(@class,'ps-menuitem-root')][.//*[normalize-space()='Dashboard']]"
)
SUCCESS = "//*[normalize-space()='New lead added!']"

# ==========================================
# HELPERS
# ==========================================

results = []
saved_by_mistake = []


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
    file_name = f"tc07_{name}.png"
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
        lambda d: value in d.find_element(By.CSS_SELECTOR, '[role="combobox"]').text
    )


def open_fresh_form():
    """Go to the dashboard first so the form starts empty every time."""
    try:
        click_safely(driver.find_element(By.XPATH, DASHBOARD_MENU))
        time.sleep(2)
    except Exception:
        driver.refresh()
        time.sleep(3)

    click_safely(
        wait.until(EC.element_to_be_clickable((By.XPATH, "//*[normalize-space()='Add New Lead']")))
    )
    for field in ("name", "phonenumber", "streetaddress", "city", "postcode", "emailaddress"):
        wait.until(EC.visibility_of_element_located((By.NAME, field)))


def fill_form(data):
    if data["name"]:
        type_into("name", data["name"])
    if data["type"]:
        select_lead_type(data["type"])
    for key in TEXT_FIELDS:
        if data[key]:
            type_into(key, data[key])


def lead_was_saved(seconds):
    try:
        WebDriverWait(driver, seconds).until(
            EC.visibility_of_element_located((By.XPATH, SUCCESS))
        )
        return True
    except TimeoutException:
        return False


def block_message():
    """The warning shown when the system refuses the form (or '')."""
    message = driver.execute_script(
        "var f = document.querySelector(':invalid'); return f ? f.validationMessage : '';"
    )
    if message:
        return message
    for selector in (".MuiFormHelperText-root.Mui-error", '[role="alert"]', ".error"):
        for element in driver.find_elements(By.CSS_SELECTOR, selector):
            if element.is_displayed() and element.text.strip():
                return element.text.strip()
    return ""


# ==========================================
# TEST
# ==========================================

print()
print("==========================================")
print("TC-LDS-07: ADD LEAD WITH EMPTY REQUIRED FIELD (Jira WEB-2)")
print("==========================================")

current = "starting"

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
    time.sleep(2)

    # ---- Step 1 ----
    current = "Step 1 - click 'Add New Lead' in the sidebar"
    open_fresh_form()
    record("PASS", "Step 1: the Add New Lead form is displayed.")

    # ---- Steps 2 to 9 ----
    for step, label, empty_keys in STEPS:
        current = f"Step {step} - leave {label} empty and click Submit"
        print(f"\n--- Step {step}: {label} left empty ---")

        if step != 2:
            open_fresh_form()

        data = {key: ("" if key in empty_keys else value) for key, value in FULL.items()}
        if data["name"]:
            data["name"] = f"{FULL['name']} {STAMP}-S{step}"

        fill_form(data)
        click_safely(
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]')))
        )

        saved = lead_was_saved(4)
        warning = "" if saved else block_message()
        if not saved and not warning:
            saved = lead_was_saved(10)  # the server may be slow

        shot(f"step{step}")

        if saved:
            saved_by_mistake.append(data["name"] or f"(no name, step {step})")
            record(
                "FAIL",
                f"Step {step}: {label} left empty -> the system SAVED the lead "
                "(success message shown). Expected: blocked with a validation message.",
            )
            try:
                wait.until(EC.invisibility_of_element_located((By.XPATH, SUCCESS)))
            except TimeoutException:
                pass
        else:
            shown = f'validation message: "{warning}"' if warning else "no success message, lead not added"
            record("PASS", f"Step {step}: {label} left empty -> the system blocked it ({shown}).")

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
failed = [text for status, text in results if status == "FAIL"]

print()
print("==========================================")
print("TC-LDS-07 SUMMARY")
print("------------------------------------------")
for status, text in results:
    print(f"[{status}] {text}")
print("------------------------------------------")
if saved_by_mistake:
    print("Leads saved by mistake (delete these in the system):")
    for name in saved_by_mistake:
        print(f"  - {name}")
    print("------------------------------------------")
if has_error:
    print("RESULT: INCOMPLETE - the script could not finish, so this is not a test result.")
elif failed:
    print(f"RESULT: FAILED - {len(failed)} step(s) saved a lead with empty required field(s) (matches WEB-2).")
else:
    print("RESULT: PASSED - the system blocked every empty required field.")
print("==========================================")

sys.exit(1 if (has_error or failed) else 0)
