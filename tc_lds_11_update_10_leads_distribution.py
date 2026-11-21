"""
TC-LDS-11 | Telemarketer Module - Update 10 Leads x Distribution | Jira: WEB-5

After the telemarketer has updated ALL leads of the current batch, the system
must distribute the next batch of 10 undistributed leads.

Steps (same as the test case in the spreadsheet):
  1. Click "Leads" -> the Assigned Leads page lists the current batch of 10 leads
  2. Update the Call Disposition of the first 9 leads
     -> each update is saved, no new batch is distributed yet
  3-4. Update the Call Disposition of the 10th lead
     -> the system distributes a new batch of 10 undistributed leads

Needs (preconditions of the test case):
  - a telemarketer with a current batch of 10 assigned leads
  - additional undistributed leads in the system

The batch size is read from the page, so a batch of 8 (the known defect) is
updated completely and then the new batch is counted: expected 10.

This script CHANGES the Call Disposition of every assigned lead to the value
set in DISPOSITION below.
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
EXPECTED_BATCH = 10


# ==========================================
# HELPERS
# ==========================================


def leads_page(qa):
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


def update_disposition(qa, lead_id):
    """Edit icon > select the Call Disposition > Update."""
    qa.close_dialogs()
    qa.open_menu(LEADS_LABELS)
    qa.wait_for_rows()
    row = qa.find_row(lead_id)
    if row is None:
        raise TimeoutException(f"lead {lead_id} is not in the Assigned Leads list")
    qa.click(qa.row_action(row, ("EditIcon", "ModeEditIcon", "EditOutlinedIcon"), 1))
    update_button = qa.visible("//button[normalize-space()='Update']", 20)
    if update_button is None:
        raise TimeoutException("the Update Lead form did not open")
    time.sleep(1)

    # The Call Disposition is the last dropdown of the form (Type is the first).
    dropdowns = [
        e
        for e in qa.driver.find_elements(By.CSS_SELECTOR, '[role="combobox"]')
        if e.is_displayed()
    ]
    if not dropdowns:
        raise TimeoutException("no dropdown found in the Update Lead form")
    qa.choose_option(dropdowns[-1], DISPOSITION)

    qa.click(update_button)
    time.sleep(3)
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
    batch_ids, batch_size = leads_page(qa)
    qa.shot("1_current_batch")
    print(f"    Leads in the current batch: {batch_size}")
    if batch_size == EXPECTED_BATCH:
        qa.record("PASS", f"Step 1: the Assigned Leads page lists the current batch of {EXPECTED_BATCH} leads.")
    else:
        qa.record(
            "FAIL",
            f"Step 1: expected the current batch of {EXPECTED_BATCH} leads. "
            f"Actual: the Assigned Leads page lists {batch_size}.",
        )
    if not batch_ids:
        raise TimeoutException("no assigned leads are listed, so there is nothing to update")

    # ---- Step 2: all leads except the last ----
    qa.step(f"Step 2 - update the Call Disposition of the first {len(batch_ids) - 1} leads")
    for number, lead_id in enumerate(batch_ids[:-1], start=1):
        update_disposition(qa, lead_id)
        print(f"    Updated lead {number} of {len(batch_ids)} ({lead_id})")

    ids_now, _ = leads_page(qa)
    new_early = set(ids_now) - set(batch_ids)
    qa.shot("2_before_last_update")
    if new_early:
        qa.record(
            "FAIL",
            f"Step 2: a new batch ({len(new_early)} leads) was distributed BEFORE the last lead was updated.",
        )
    else:
        qa.record("PASS", f"Step 2: each update was saved and no new batch was distributed yet.")

    # ---- Steps 3-4: the last lead ----
    qa.step("Steps 3-4 - update the last lead and check the new batch")
    update_disposition(qa, batch_ids[-1])
    print(f"    Updated lead {len(batch_ids)} of {len(batch_ids)} ({batch_ids[-1]})")
    qa.record("PASS", "Step 3: the last update was saved. All leads of the batch are updated.")

    time.sleep(3)
    ids_after, _ = leads_page(qa)
    qa.shot("3_new_batch")
    new_leads = set(ids_after) - set(batch_ids)
    print(f"    New leads distributed: {len(new_leads)}")

    if len(new_leads) == EXPECTED_BATCH:
        qa.record("PASS", f"Step 4: the system distributed a new batch of {EXPECTED_BATCH} undistributed leads.")
    else:
        qa.record(
            "FAIL",
            f"Step 4: expected a new batch of {EXPECTED_BATCH} undistributed leads. "
            f"Actual: only {len(new_leads)} new leads were distributed.",
        )


qa = QA("TC-LDS-11", "Telemarketer Module - Update 10 Leads x Distribution", "WEB-5", WEBSITE, HEADLESS)
qa.execute(test)
