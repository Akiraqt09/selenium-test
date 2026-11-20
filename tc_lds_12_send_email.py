"""
TC-LDS-12 | Telemarketer Module - Send Email | Jira: WEB-6

A telemarketer must be able to send an email to a lead with the Send An Email
window.

Steps (same as the test case in the spreadsheet):
  1. Click "Leads", then the email icon of an assigned lead
     -> the Send An Email window is displayed (From, To, Subject, Text, Send)
  2. Select a Subject -> the email body message is populated automatically
  3. Customize the message -> the edited message is accepted
  4. Click Send -> the email is sent, a success message is displayed and the
     email appears in the Emails Sent list

Known defect (WEB-6): clicking the email icon logs out the user, so steps 2-4
cannot be done.

SAFETY: step 4 sends a REAL email to the lead's address. It is only done when
SEND_THE_EMAIL is True. The default is False.
"""

import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from qa_helpers import LEADS_LABELS, QA, text_contains_ci

# ==========================================
# SETTINGS
# ==========================================

# Use "http://localhost:3000/" to test your own copy of the system.
WEBSITE = "https://sortrleaddistribution-client.onrender.com/"
HEADLESS = True  # False = show the browser window (on a computer)

# Telemarketer test account
EMAIL = "emmandc0908@gmail.com"
PASSWORD = "ABCabc123!"

MESSAGE = "Hello, we would like to follow up on your inquiry."
SEND_THE_EMAIL = False  # True = really click Send (sends a real email)

MODAL_TITLE = "//*[normalize-space()='Send An Email']"
TEXT_AREA = "//textarea[@name='text']"
SEND_BUTTON = "//button[@type='submit' and normalize-space()='Send']"
SUBJECT_DROPDOWN = (
    "//*[normalize-space()='Subject']"
    "/ancestor::div[contains(@class,'MuiFormControl-root')]"
    "//*[@role='combobox' or @aria-haspopup='listbox']"
)


def test(qa):
    qa.step("Precondition - log in as a Telemarketer")
    qa.login(EMAIL, PASSWORD)
    qa.record("PASS", "Precondition: logged in as a Telemarketer.")

    # ---- Step 1 ----
    qa.step("Step 1 - click 'Leads' and the email icon of an assigned lead")
    qa.open_menu(LEADS_LABELS)
    rows = qa.wait_for_rows()
    if not rows:
        raise TimeoutException("no assigned lead is listed (the test needs at least one)")
    qa.shot("1_assigned_leads")

    email_icon = qa.row_action(rows[0], ("AttachEmailIcon", "EmailIcon"), 3)
    qa.click(email_icon)

    modal = qa.visible(MODAL_TITLE, seconds=15)
    qa.shot("2_after_email_icon")

    if modal is None:
        if qa.logged_out():
            actual = "the system LOGGED OUT the user (the login page is displayed)"
        else:
            actual = f"the Send An Email window did not open (current page: {qa.driver.current_url})"
        qa.record(
            "FAIL",
            "Step 1: expected the Send An Email window with From, To, Subject, Text and Send. "
            f"Actual: {actual}.",
        )
        for number, text in (
            (2, "select a Subject"),
            (3, "customize the message"),
            (4, "click Send"),
        ):
            qa.record("SKIP", f"Step {number}: {text} - not run, the Send An Email window did not open.")
        return

    has_fields = (
        qa.any_visible(TEXT_AREA) is not None and qa.any_visible(SEND_BUTTON) is not None
    )
    if has_fields:
        qa.record("PASS", "Step 1: the Send An Email window is displayed with the Text field and Send button.")
    else:
        qa.record("FAIL", "Step 1: the Send An Email window opened but the Text field or Send button is missing.")

    # ---- Step 2 ----
    qa.step("Step 2 - select a Subject")
    dropdown = qa.visible(SUBJECT_DROPDOWN, 15)
    if dropdown is None:
        raise TimeoutException("the Subject dropdown was not found")
    qa.click(dropdown)
    option = qa.visible("//li[@role='option']", 15)
    if option is None:
        raise TimeoutException("the Subject dropdown has no options")
    qa.click(option)
    time.sleep(2)
    body = qa.driver.find_element(By.XPATH, TEXT_AREA).get_attribute("value").strip()
    if body:
        qa.record("PASS", "Step 2: the email body message is populated automatically.")
    else:
        qa.record("FAIL", "Step 2: expected the email body message to be populated. Actual: the Text field is empty.")

    # ---- Step 3 ----
    qa.step("Step 3 - customize the message")
    text_area = qa.driver.find_element(By.XPATH, TEXT_AREA)
    qa.clear_text(text_area)
    text_area.send_keys(MESSAGE)
    if text_area.get_attribute("value").strip() == MESSAGE:
        qa.record("PASS", "Step 3: the edited message is accepted.")
    else:
        qa.record("FAIL", "Step 3: the edited message was not accepted.")

    # ---- Step 4 ----
    qa.step("Step 4 - click the Send button")
    qa.shot("3_email_ready")
    if not SEND_THE_EMAIL:
        qa.record("SKIP", "Step 4: Send was not clicked (SEND_THE_EMAIL is False, so no real email is sent).")
        return

    qa.click(qa.driver.find_element(By.XPATH, SEND_BUTTON))
    confirmation = qa.visible(
        f"//*[{text_contains_ci('sent')} or {text_contains_ci('success')}]", seconds=15
    )
    qa.shot("4_after_send")
    if confirmation is not None:
        qa.record("PASS", f'Step 4: the system sent the email and displayed: "{confirmation.text.strip()[:80]}".')
    else:
        qa.record("FAIL", "Step 4: expected the email to be sent with a success message. Actual: no success message appeared.")


qa = QA("TC-LDS-12", "Telemarketer Module - Send Email", "WEB-6", WEBSITE, HEADLESS)
qa.execute(test)
