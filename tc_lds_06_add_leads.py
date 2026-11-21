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
HEADLESS = False

# Test input from TC-LDS-06. A time stamp is added to the name so this
# run's lead cannot be confused with a lead from an earlier run.
STAMP = datetime.now().strftime("%H%M%S")
LEAD_NAME = f"Emmanuel {STAMP}"
LEAD_TYPE = "Schools"
PHONE = "61 288 8802 1234"
STREET = "33 Main Street"
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


def lead_is_listed(name, seconds=20):
    """
    True if the lead name is visible on the current page.
    More robust version for MUI DataGrid:
    - Tries the search box if present
    - Uses a flexible contains() XPath
    - Falls back to checking page source / all text nodes
    - Prints visible lead names for debugging when not found
    """
    # Optional: use the search/filter box if it exists
    try:
        # MUI DataGrid quick filter / search
        search_selectors = [
            'input[placeholder="Search"]',
            'input[placeholder*="Search"]',
            'input[type="search"]',
            '.MuiDataGrid-toolbar input',
            'input[aria-label*="Search"]',
        ]
        box = None
        for sel in search_selectors:
            try:
                box = driver.find_element(By.CSS_SELECTOR, sel)
                if box.is_displayed():
                    break
            except Exception:
                continue

        if box:
            box.clear()
            box.send_keys(name)
            time.sleep(1.5)  # let the grid filter
    except Exception:
        pass

    # Primary check – flexible contains (handles extra whitespace / nested elements)
    xpath_contains = f"//*[contains(normalize-space(), '{name}')]"
    try:
        WebDriverWait(driver, seconds).until(
            EC.visibility_of_element_located((By.XPATH, xpath_contains))
        )
        return True
    except TimeoutException:
        pass

    # Fallback: check if the name appears anywhere in the body text
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if name in body_text:
            return True
    except Exception:
        pass

    # Debug help: print some of the visible names so we can see what the grid actually shows
    try:
        # Try to collect names from common DataGrid cell patterns
        cells = driver.find_elements(By.CSS_SELECTOR, ".MuiDataGrid-cell, td, [role='cell']")
        visible_names = []
        for cell in cells[:40]:  # limit output
            txt = cell.text.strip()
            if txt and len(txt) > 3 and not txt.isdigit():
                visible_names.append(txt)
        if visible_names:
            print("    Visible text samples on the page:")
            for n in visible_names[:15]:
                print(f"      - {n}")
    except Exception:
        pass

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

    email_field = wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))
    )
    email_field.clear()
    email_field.send_keys(EMAIL)

    password_field = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
    password_field.clear()
    password_field.send_keys(PASSWORD)

    click_safely(
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Log In']")))
    )

    # Wait for the dashboard to appear
    wait.until(
        EC.visibility_of_element_located((By.XPATH, "//*[normalize-space()='DASHBOARD' or contains(text(),'Lead Generation')]"))
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

    # Prefer clicking the actual menu button (more reliable with the current sidebar)
    try:
        leads_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@class,'ps-menu-button')][normalize-space()='Leads' or normalize-space()='Leeds']")
            )
        )
        click_safely(leads_btn)
    except TimeoutException:
        # Fallback to the older li-based locator
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

    # Wait until we are actually on the Leads page
    try:
        WebDriverWait(driver, 15).until(
            lambda d: "LeadGenLeads" in d.current_url or "LEADS" in d.find_element(By.TAG_NAME, "body").text
        )
    except TimeoutException:
        print("    Warning: URL/title did not change to Leads page as expected.")

    time.sleep(3)  # extra time for the DataGrid to render rows

    found = lead_is_listed(LEAD_NAME, 20)
    if not found:
        print("    Not found yet. Refreshing the page and checking once more...")
        driver.refresh()
        time.sleep(5)
        # Wait again for the grid after refresh
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".MuiDataGrid-root, table, [role='grid']"))
            )
        except TimeoutException:
            pass
        found = lead_is_listed(LEAD_NAME, 20)

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
