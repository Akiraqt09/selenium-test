"""
TC-LDS-17 | Team Leader Module - Add User | Jira: WEB-9

A Team Leader must be able to create a new user account and assign the role.

Steps (same as the test case in the spreadsheet):
  1. Click "Add New User" in the sidebar
     -> the Create New User form is displayed (Full Name, Email, Password,
        Select Role, Add New User button)
  2. Enter the Full Name
  3. Enter the Email and Password
  4. Select a Role (Telemarketer)
  5. Click the Add New User button
     -> the system creates the user and displays a success message;
        the new user appears in the Users list with the selected role

Known defect (WEB-9): after the user is added, the system redirects to the
Leads list instead of the Users list, and the new user does not appear in the
Users list.

This script creates a REAL user. A time stamp is added to the email so the
email is not registered yet (a precondition of the test case). Delete the user
afterwards if you do not want to keep it.
"""

import time
from datetime import datetime

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from qa_helpers import ADD_USER_LABELS, QA, USERS_LABELS

# ==========================================
# SETTINGS
# ==========================================

# Use "http://localhost:3000/" to test your own copy of the system.
WEBSITE = "https://sortrleaddistribution-client.onrender.com/"
HEADLESS = True  # False = show the browser window (on a computer)

# Team Leader test account
EMAIL = "sorianoivan13@gmail.com"
PASSWORD = "ABCabc123!"

# Test input from TC-LDS-17 (the email gets a time stamp so it is new)
STAMP = datetime.now().strftime("%H%M%S")
FULL_NAME = "Juan Dela Cruz"
NEW_EMAIL = f"juan.delacruz{STAMP}@example.com"
NEW_PASSWORD = "Juan@Pass2024!"
ROLE = "Telemarketer"

def form_fields(qa):
    """(full name, email, password, role dropdown) of the Create New User form."""
    driver = qa.driver
    visible = lambda elements: [e for e in elements if e.is_displayed()]
    email = visible(driver.find_elements(By.CSS_SELECTOR, 'input[type="email"]'))
    password = visible(driver.find_elements(By.CSS_SELECTOR, 'input[type="password"]'))
    role = visible(driver.find_elements(By.CSS_SELECTOR, '[role="combobox"]'))
    names = [
        e
        for e in visible(driver.find_elements(By.CSS_SELECTOR, 'input[type="text"], input:not([type])'))
        if (e.get_attribute("placeholder") or "") != "Search"
        and not e.get_attribute("aria-hidden")
        and e.get_attribute("role") != "combobox"
    ]
    if not (names and email and password and role):
        raise TimeoutException(
            f"form fields not found (name {len(names)}, email {len(email)}, "
            f"password {len(password)}, role {len(role)})"
        )
    return names[0], email[0], password[0], role[0]


def test(qa):
    qa.step("Precondition - log in as a Team Leader")
    qa.login(EMAIL, PASSWORD)
    qa.record("PASS", "Precondition: logged in as a Team Leader.")

    # ---- Step 1 ----
    qa.step("Step 1 - click 'Add New User' in the sidebar")
    qa.open_menu(ADD_USER_LABELS)
    submit_xpath = "//button[normalize-space()='Add New User']"
    if qa.visible(submit_xpath, 20) is None:
        raise TimeoutException("the Create New User form did not open")
    full_name, email, password, role = form_fields(qa)
    qa.shot("1_create_user_form")
    qa.record(
        "PASS",
        "Step 1: the Create New User form is displayed with Full Name, Email, Password, "
        "Select Role and an Add New User button.",
    )

    # ---- Step 2 ----
    qa.step("Step 2 - enter the Full Name")
    full_name.send_keys(FULL_NAME)
    qa.record("PASS", f"Step 2: Full Name is accepted ({FULL_NAME}).")

    # ---- Step 3 ----
    qa.step("Step 3 - enter the Email and Password")
    email.send_keys(NEW_EMAIL)
    password.send_keys(NEW_PASSWORD)
    if password.get_attribute("type") == "password":
        qa.record("PASS", f"Step 3: Email is accepted ({NEW_EMAIL}). Password is accepted and masked.")
    else:
        qa.record("FAIL", "Step 3: the Password is not masked.")

    # ---- Step 4 ----
    qa.step("Step 4 - select a Role")
    qa.choose_option(role, ROLE)
    qa.record("PASS", f"Step 4: the selected role is displayed ({ROLE}).")

    # ---- Step 5 ----
    qa.step("Step 5 - click the Add New User button")
    qa.shot("2_form_filled")
    qa.click(qa.driver.find_element(By.XPATH, submit_xpath))
    time.sleep(3)
    qa.shot("3_after_submit")

    popup = qa.any_visible("//*[@role='dialog']")
    message = popup.text.strip().replace("\n", " ")[:80] if popup is not None else ""
    if popup is not None:
        button = qa.any_visible(
            "//*[@role='dialog']//button[normalize-space()='OK' or normalize-space()='Close' "
            "or normalize-space()='Okay' or normalize-space()='Continue']"
        )
        if button is not None:
            qa.click(button)
    time.sleep(3)

    if message:
        qa.record("PASS", f'Step 5: the system displayed a message: "{message}".')
    else:
        qa.record("INFO", "Step 5: no success message was found.")

    url = qa.driver.current_url
    qa.shot("4_page_after_adding")
    print(f"    Page after adding the user: {url}")
    if "adminusers" in url.lower() or "users" in url.lower().split("/")[-1]:
        qa.record("PASS", "Step 5: the system shows the Users list after adding the user.")
    else:
        qa.record(
            "FAIL",
            f"Step 5: expected the Users list after adding the user. Actual: the system redirected to {url} "
            "(the Leads list).",
        )

    # ---- The new user in the Users list ----
    qa.step("Step 5 - check that the new user appears in the Users list")
    qa.open_menu(USERS_LABELS)
    search = qa.any_visible("//input[@placeholder='Search']")
    if search is not None:
        search.clear()
        search.send_keys(NEW_EMAIL)
        time.sleep(2)
    found = qa.visible(f"//*[normalize-space()='{NEW_EMAIL}']", seconds=10)
    qa.shot("5_users_list")
    if found is None:
        qa.record("FAIL", f"Step 5: expected the new user ({NEW_EMAIL}) in the Users list. Actual: the user is not listed.")
    else:
        row_text = found.find_element(By.XPATH, "./ancestor::*[@role='row'][1]").text
        if ROLE.lower() in row_text.lower():
            qa.record("PASS", f"Step 5: the new user appears in the Users list with the role {ROLE}.")
        else:
            qa.record("FAIL", f"Step 5: the new user is listed but without the role {ROLE} ({row_text!r}).")


qa = QA("TC-LDS-17", "Team Leader Module - Add User", "WEB-9", WEBSITE, HEADLESS)
qa.execute(test)
