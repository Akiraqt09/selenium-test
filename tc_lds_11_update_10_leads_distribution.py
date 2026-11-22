"""
TC-LDS-11 | Telemarketer Module - Update 10 Leads x Distribution | Jira: WEB-5

After the telemarketer has updated 10 leads, the system must distribute a new
batch of 10 undistributed leads.

Steps:
  1. Click "Leads" -> the Assigned Leads page lists AT LEAST 10 assigned leads
     (fewer than 10 = FAIL)
  2. Update the Call Disposition of the first 9 of the leads
     -> each update is saved, no new batch is distributed yet
  3-4. Update the Call Disposition of the 10th lead
     -> the system distributes a new batch of 10 undistributed leads

Only 10 leads are updated, even if more are assigned. The leads that were
assigned before the updates are remembered, so the new batch is counted as the
leads that were NOT in the list before.

Needs (preconditions of the test case):
  - a telemarketer with at least 10 assigned leads
  - additional undistributed leads in the system

This script CHANGES the Call Disposition of 10 leads to DISPOSITION below.
"""

import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from qa_helpers import LEADS_LABELS, QA

# ==========================================
# SETTINGS
# ==========================================

# Use "http://localhost:3000/" to test your own copy of the system.
WEBSITE = "https://sortrleaddistribution-client.onrender.com/"
HEADLESS = True  # False = show the browser window (on a computer)

# Telemarketer test account
EMAIL = "emmandc0908@gmail.com"
PASSWORD = "ABCabc123"

DISPOSITION = "Warm Lead"
MIN_ASSIGNED = 10      # step 1: at least this many assigned leads
LEADS_TO_UPDATE = 10   # step 2-4: how many leads are updated
NEW_BATCH = 10         # step 4: size of the new batch that must be distributed

UPDATE_BUTTON = "//button[normalize-space()='Update']"

# The Update Lead form fields, in order: Lead Name, Type, Phone Number,
# Street Address, City, Postcode, Email Address, Call Disposition, Remarks.
CALL_DISPOSITION_INDEX = 7
CONTROL_SELECTOR = (
    'input:not([type="hidden"]):not([type="checkbox"]):not([aria-hidden="true"])'
    ":not(.MuiSelect-nativeInput), "
    'textarea:not([aria-hidden="true"]), [role="combobox"]'
)


# ==========================================
# HELPERS
# ==========================================


def leads_page(qa):
    """Open the Assigned Leads page. Returns (ids of the leads, total)."""
    qa.open_menu(LEADS_LABELS)
    rows = qa.wait_for_rows()
    ids = [qa.row_id(row) for row in rows]
    total = qa.grid_total()
    return ids, (total if total is not None else len(ids))


def dismiss_popup(qa):
    button = qa.any_visible(
        "//*[@role='dialog']//button[normalize-space()='OK' or normalize-space()='Close' "
        "or normalize-space()='Okay' or normalize-space()='Continue']"
    )
    if button is not None:
        qa.click(button)
        time.sleep(1)


def form_controls(qa):
    container = None
    for xpath in ("//*[@role='dialog']", "//form"):
        container = qa.any_visible(xpath)
        if container is not None:
            break
    scope = container if container is not None else qa.driver
    controls = []
    for element in scope.find_elements(By.CSS_SELECTOR, CONTROL_SELECTOR):
        if not element.is_displayed():
            continue
        if (element.get_attribute("placeholder") or "") == "Search":
            continue
        controls.append(element)
    return controls


def describe(element):
    value = (element.get_attribute("value") or element.text or "").strip()
    return (
        f"{element.tag_name} role={element.get_attribute('role')!r} "
        f"name={element.get_attribute('name')!r} value={value!r}"
    )


def wait_for_form_controls(qa, minimum=8, seconds=15):
    """The form fields can appear a moment after the Update button does."""
    end = time.time() + seconds
    controls = []
    while time.time() < end:
        controls = form_controls(qa)
        if len(controls) >= minimum:
            return controls
        time.sleep(0.5)
    return controls


def set_call_disposition(qa, control):
    if control.get_attribute("role") == "combobox" and control.tag_name != "input":
        qa.choose_option(control, DISPOSITION)  # a dropdown list
        return
    # a text box (it may show a list of suggestions)
    qa.clear_text(control)
    control.send_keys(DISPOSITION)
    time.sleep(0.5)
    options = qa.driver.find_elements(
        By.XPATH, f"//li[@role='option'][normalize-space()='{DISPOSITION}']"
    )
    if options:
        qa.driver.execute_script("arguments[0].click();", options[0])


def update_disposition(qa, lead_id):
    """Edit icon > select the Call Disposition > Update."""
    qa.close_dialogs()
    qa.open_menu(LEADS_LABELS)
    qa.wait_for_rows()
    row = qa.find_row(lead_id)
    if row is None:
        raise TimeoutException(f"lead {lead_id} is not in the Assigned Leads list")
    qa.click(qa.row_action(row, ("EditIcon", "ModeEditIcon", "EditOutlinedIcon"), 1))
    if qa.visible(UPDATE_BUTTON, 20) is None:
        raise TimeoutException("the Update Lead form did not open")

    controls = wait_for_form_controls(qa)
    if len(controls) == 9:
        disposition = controls[CALL_DISPOSITION_INDEX]
    else:
        print(f"    Form fields found: {len(controls)} (expected 9)")
        for number, control in enumerate(controls, start=1):
            print(f"      {number}. {describe(control)}")
        qa.shot("form_fields")
        raise TimeoutException(
            "the Call Disposition field of the Update Lead form was not found "
            "(send the list printed above so the script can be adjusted)"
        )

    set_call_disposition(qa, disposition)
    qa.click(qa.visible(UPDATE_BUTTON, 10))
    time.sleep(2)
    dismiss_popup(qa)
    qa.close_dialogs()


# ==========================================
# TEST
# ==========================================


def test(qa):
    qa.step("Precondition - log in as a Telemarketer")
    qa.login(EMAIL, PASSWORD)
    qa.record("PASS", "Precondition: logged in as a Telemarketer.")

    # ---- Step 1 ----
    qa.step("Step 1 - click 'Leads' in the sidebar")
    before_ids, total = leads_page(qa)
    qa.shot("1_assigned_leads")
    print(f"    Assigned leads listed: {total}")
    if total >= MIN_ASSIGNED:
        qa.record("PASS", f"Step 1: the Assigned Leads page lists at least {MIN_ASSIGNED} leads ({total} listed).")
    else:
        qa.record(
            "FAIL",
            f"Step 1: expected at least {MIN_ASSIGNED} assigned leads. "
            f"Actual: the Assigned Leads page lists only {total}.",
        )
    if not before_ids:
        raise TimeoutException("no assigned leads are listed, so there is nothing to update")

    to_update = before_ids[:LEADS_TO_UPDATE]
    if len(to_update) < LEADS_TO_UPDATE:
        print(f"    Only {len(to_update)} leads can be updated (fewer than {LEADS_TO_UPDATE} are assigned).")

    # ---- Step 2: all of the 10 leads except the last ----
    qa.step(f"Step 2 - update the Call Disposition of the first {len(to_update) - 1} leads")
    for number, lead_id in enumerate(to_update[:-1], start=1):
        update_disposition(qa, lead_id)
        print(f"    Updated lead {number} of {len(to_update)} ({lead_id})")

    ids_now, _ = leads_page(qa)
    new_early = set(ids_now) - set(before_ids)
    qa.shot("2_before_last_update")
    if new_early:
        qa.record(
            "FAIL",
            f"Step 2: a new batch ({len(new_early)} leads) was distributed BEFORE the last lead was updated.",
        )
    else:
        qa.record("PASS", "Step 2: each update was saved and no new batch was distributed yet.")

    # ---- Steps 3-4: the last lead ----
    qa.step("Steps 3-4 - update the last lead and check the new batch")
    update_disposition(qa, to_update[-1])
    print(f"    Updated lead {len(to_update)} of {len(to_update)} ({to_update[-1]})")
    qa.record("PASS", f"Step 3: the last update was saved. {len(to_update)} leads are updated.")

    time.sleep(3)
    ids_after, _ = leads_page(qa)
    qa.shot("3_new_batch")
    new_leads = set(ids_after) - set(before_ids)
    print(f"    New leads distributed: {len(new_leads)}")

    if len(new_leads) == NEW_BATCH:
        qa.record("PASS", f"Step 4: the system distributed a new batch of {NEW_BATCH} undistributed leads.")
    else:
        qa.record(
            "FAIL",
            f"Step 4: expected a new batch of {NEW_BATCH} undistributed leads. "
            f"Actual: {len(new_leads)} new leads were distributed.",
        )


qa = QA("TC-LDS-11", "Telemarketer Module - Update 10 Leads x Distribution", "WEB-5", WEBSITE, HEADLESS)
qa.execute(test)
