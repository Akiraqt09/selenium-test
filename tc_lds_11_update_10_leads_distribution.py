"""
TC-LDS-11 | Telemarketer Module - Update 10 Leads x Distribution | Jira: WEB-5

After the telemarketer has updated the assigned leads, the system must
distribute a new batch of 10 undistributed leads.

Steps:
  1. Click "Leads" -> the Assigned Leads page lists AT LEAST 10 assigned leads
     (fewer than 10 = FAIL)
  2. Update the Call Disposition of the leads, one by one
     -> each update is saved, no new batch is distributed yet
  3-4. Update the LAST lead
     -> the system distributes a new batch of 10 undistributed leads

IMPORTANT - every update is checked:
  The Update Lead form has REQUIRED fields (Remarks, Email, Phone ...). When one
  of them is empty the system refuses the update and the lead is NOT updated,
  so no new batch can follow. The script therefore
    - fills in Remarks when it is empty,
    - fills in other empty required fields with sample data when
      FILL_MISSING is True,
    - removes the spaces from the phone number (the form only accepts digits,
      for example 61269213368 - "61 2 6921 3368" is refused),
    - checks that the window really closed, and reports every lead that
      could not be updated (and why),
    - checks that the Call Disposition column of the list shows the new value.

The new batch is looked for 3 ways: on the list right after the last update,
after refreshing the page, and after logging in again (the system also hands
out leads at log in). The summary says where the new leads showed up.

Needs: at least 10 assigned leads and more undistributed leads in the system.
"""

import re
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
REMARKS = "Callback later @11am."
MIN_ASSIGNED = 10      # step 1: at least this many assigned leads
LEADS_TO_UPDATE = 100  # how many leads are updated (100 = ALL assigned leads)
NEW_BATCH = 10         # step 4: size of the new batch that must be distributed

# True = a lead with an empty required field (for example no email) gets sample
# data so that the update can be saved. This CHANGES that lead's data.
FILL_MISSING = True
SAMPLE = {
    2: "61255501234",                 # Phone Number (digits only, no spaces)
    3: "12 Main Street",              # Street Address
    4: "Wagga Wagga",                 # City
    5: "2650",                        # Postcode
    6: "oceanview.cafe@example.com",  # Email Address
}
SAMPLE_TYPE = "Cafe"

UPDATE_BUTTON = "//button[normalize-space()='Update']"
OK_BUTTON = (
    "//*[@role='dialog']//button[normalize-space()='OK' or normalize-space()='Close' "
    "or normalize-space()='Okay' or normalize-space()='Continue']"
)

# The Update Lead form fields, in order: 0 Lead Name, 1 Type, 2 Phone Number,
# 3 Street Address, 4 City, 5 Postcode, 6 Email Address, 7 Call Disposition,
# 8 Remarks.
TYPE_INDEX = 1
PHONE_INDEX = 2
CALL_DISPOSITION_INDEX = 7
REMARKS_INDEX = 8
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
    qa.open_menu(LEADS_LABELS, wait_seconds=1)
    rows = qa.wait_for_rows()
    ids = [qa.row_id(row) for row in rows]
    total = qa.grid_total()
    return ids, (total if total is not None else len(ids))


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


def value_of(element):
    return (element.get_attribute("value") or element.text or "").strip()


def is_empty(element):
    return value_of(element).lower() in ("", "choose one")


def describe(element):
    return (
        f"{element.tag_name} role={element.get_attribute('role')!r} "
        f"name={element.get_attribute('name')!r} value={value_of(element)!r}"
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


def pick_option(qa, control, text):
    """Open a dropdown and click the option (even if the list must be scrolled)."""
    qa.click(control)
    xpath = f"//li[@role='option'][normalize-space()='{text}' or @data-value='{text}']"
    end = time.time() + 8
    while time.time() < end:
        found = qa.driver.find_elements(By.XPATH, xpath)
        if found:
            qa.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", found[0]
            )
            return
        time.sleep(0.1)
    raise TimeoutException(f"Dropdown option not found: {text}")


def set_call_disposition(qa, control):
    if control.get_attribute("role") == "combobox" and control.tag_name != "input":
        pick_option(qa, control, DISPOSITION)  # a dropdown list
        return
    qa.clear_text(control)  # a text box (it may show a list of suggestions)
    control.send_keys(DISPOSITION)
    time.sleep(0.5)
    options = qa.driver.find_elements(
        By.XPATH, f"//li[@role='option'][normalize-space()='{DISPOSITION}']"
    )
    if options:
        qa.driver.execute_script("arguments[0].click();", options[0])


def type_text(qa, control, text):
    qa.clear_text(control)
    control.send_keys(text)


JS_INVALID_FIELDS = """
var out = [];
document.querySelectorAll('input:invalid, textarea:invalid, select:invalid').forEach(function (e) {
  var label = '';
  var box = e.closest('.MuiFormControl-root');
  if (box) { var l = box.querySelector('label'); if (l) { label = l.innerText; } }
  out.push({name: e.name || '', label: label, value: e.value, message: e.validationMessage,
            pattern: e.getAttribute('pattern') || '', maxlength: e.getAttribute('maxlength') || ''});
});
return out;
"""

SAMPLE_BY_NAME = {
    "phonenumber": SAMPLE[2],
    "streetaddress": SAMPLE[3],
    "city": SAMPLE[4],
    "postcode": SAMPLE[5],
    "emailaddress": SAMPLE[6],
}


def row_info(qa, lead_id):
    """(Call Disposition, Updated At) of the lead as shown in the list, or None."""
    row = qa.find_row(lead_id)
    if row is None:
        return None
    disposition = updated = ""
    for header, text in qa.row_values(row).items():
        name = header.lower()
        if "dispos" in name or "dispus" in name:
            disposition = text.strip()
        elif name.startswith("updated"):
            updated = text.strip()
    return disposition, updated


def wait_for_update_result(qa, lead_id, before, seconds=10):
    """(True, '') when the update was saved, else (False, why not).

    Saved = the list shows the new Call Disposition (or a new Updated At),
    or the Update Lead window closed on its own."""
    start = time.time()
    while time.time() - start < seconds:
        button = qa.any_visible(OK_BUTTON)
        if button is not None:
            qa.click(button)
        info = row_info(qa, lead_id)
        if info is not None and info[0] == DISPOSITION and (
            before[0] != DISPOSITION or info[1] != before[1]
        ):
            return True, ""
        if not qa.driver.find_elements(By.CSS_SELECTOR, ".MuiModal-root"):
            return True, ""
        time.sleep(0.3)
    return False, "the Update Lead window did not close and the list did not change"


def what_blocks(qa):
    """Everything the form complains about: (invalid fields, texts of the system)."""
    invalid = qa.driver.execute_script(JS_INVALID_FIELDS) or []
    texts = []
    for element in qa.driver.find_elements(
        By.CSS_SELECTOR, ".Mui-error, [role='alert'], .MuiFormHelperText-root.Mui-error"
    ):
        if element.is_displayed() and element.text.strip():
            texts.append(element.text.strip())
    return invalid, texts


def repair(qa, invalid, texts, attempt):
    """Change the fields that the form refuses. True if something was changed."""
    changed = False
    for field in invalid:
        name = field.get("name", "")
        if not name:
            continue
        element = qa.driver.find_element(By.CSS_SELECTOR, f'[name="{name}"]')
        value = field.get("value", "")
        new_value = value
        if "0-9" in field.get("pattern", ""):
            new_value = re.sub(r"\D", "", value)  # digits only
        limit = field.get("maxlength", "")
        if limit.isdigit():
            new_value = new_value[: int(limit)]
        if (new_value == value or attempt >= 2 or not new_value) and name in SAMPLE_BY_NAME:
            new_value = SAMPLE_BY_NAME[name]  # still refused: use the sample data
        if new_value != value:
            type_text(qa, element, new_value)
            changed = True
    if not invalid and any(
        word in text.lower() for text in texts for word in ("phone", "number", "format")
    ):
        phone = qa.driver.find_elements(By.CSS_SELECTOR, '[name="phonenumber"]')
        if phone and value_of(phone[0]) != SAMPLE_BY_NAME["phonenumber"]:
            type_text(qa, phone[0], SAMPLE_BY_NAME["phonenumber"])
            changed = True
    return changed


def update_disposition(qa, lead_id):
    """Edit icon > Call Disposition > (required fields) > Update.
    Returns (True, '') when saved, otherwise (False, the reason)."""
    qa.close_dialogs()

    row = qa.find_row(lead_id)  # the list is usually already on the screen
    if row is None:
        qa.open_menu(LEADS_LABELS, wait_seconds=1)
        qa.wait_for_rows()
        row = qa.find_row(lead_id)
    if row is None:
        raise TimeoutException(f"lead {lead_id} is not in the Assigned Leads list")
    before = row_info(qa, lead_id) or ("", "")

    qa.click(qa.row_action(row, ("EditIcon", "ModeEditIcon", "EditOutlinedIcon"), 1))
    if qa.visible(UPDATE_BUTTON, 20) is None:
        raise TimeoutException("the Update Lead form did not open")

    controls = wait_for_form_controls(qa)
    if len(controls) != 9:
        print(f"    Form fields found: {len(controls)} (expected 9)")
        for number, control in enumerate(controls, start=1):
            print(f"      {number}. {describe(control)}")
        qa.shot("form_fields")
        raise TimeoutException(
            "the Update Lead form fields were not found as expected "
            "(send the list printed above so the script can be adjusted)"
        )

    set_call_disposition(qa, controls[CALL_DISPOSITION_INDEX])

    # The form needs every field: fill the empty ones
    if is_empty(controls[REMARKS_INDEX]):
        type_text(qa, controls[REMARKS_INDEX], REMARKS)
    if FILL_MISSING:
        for index, text in SAMPLE.items():
            if is_empty(controls[index]):
                type_text(qa, controls[index], text)
        if is_empty(controls[TYPE_INDEX]):
            pick_option(qa, controls[TYPE_INDEX], SAMPLE_TYPE)

    # The phone box only accepts digits ("61 2 6921 3368" is refused)
    phone = controls[PHONE_INDEX]
    current_phone = value_of(phone)
    if current_phone and not current_phone.isdigit():
        type_text(qa, phone, re.sub(r"\D", "", current_phone))

    reason = ""
    for attempt in range(3):
        qa.click(qa.visible(UPDATE_BUTTON, 10))
        saved, reason = wait_for_update_result(qa, lead_id, before)
        if saved:
            qa.close_dialogs()
            return True, ""

        # Not saved: find out exactly what the form complains about, fix it, try again
        invalid, texts = what_blocks(qa)
        problems = [
            f"{f.get('label') or f.get('name')}: '{f.get('value')}' -> {f.get('message')}"
            for f in invalid
        ]
        print(f"    Attempt {attempt + 1}: not saved. Fields refused: {problems or 'none'}; texts: {texts or 'none'}")
        reason = "; ".join(problems + texts) or reason
        if not FILL_MISSING or attempt == 2 or not repair(qa, invalid, texts, attempt):
            break

    qa.shot(f"not_saved_{lead_id[-4:]}")
    qa.close_dialogs()
    return False, reason


def disposition_shown(qa, lead_ids):
    """How many of the leads show the new Call Disposition in the list."""
    count = 0
    for lead_id in lead_ids:
        row = qa.find_row(lead_id)
        if row is None:
            continue
        for header, text in qa.row_values(row).items():
            name = header.lower()
            if ("dispos" in name or "dispus" in name) and text.strip() == DISPOSITION:
                count += 1
    return count


def new_leads(qa, before_ids):
    ids, _ = leads_page(qa)
    return set(ids) - set(before_ids)


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

    # ---- Step 2: every lead except the last ----
    qa.step(f"Step 2 - update the Call Disposition of the first {len(to_update) - 1} leads")
    not_saved = []
    started = time.time()
    for number, lead_id in enumerate(to_update[:-1], start=1):
        lead_start = time.time()
        saved, reason = update_disposition(qa, lead_id)
        if saved:
            print(f"    Updated lead {number} of {len(to_update)} ({lead_id}) in {time.time() - lead_start:.1f}s")
        else:
            print(f"    NOT updated: lead {number} of {len(to_update)} ({lead_id}) - {reason}")
            not_saved.append((lead_id, reason))

    if not_saved:
        shown = "; ".join(f"{lead_id}: {reason}" for lead_id, reason in not_saved[:3])
        qa.record(
            "ERROR",
            f"Step 2: {len(not_saved)} lead(s) could not be updated, so the new batch can not be "
            f"expected ({shown}). Check FILL_MISSING and the screenshots tc_lds_11_not_saved_*.png.",
        )
        return

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
    qa.step("Steps 3-4 - update the last lead and look for the new batch")
    lead_start = time.time()
    saved, reason = update_disposition(qa, to_update[-1])
    if not saved:
        qa.record("ERROR", f"Step 3: the last lead could not be updated ({reason}).")
        return
    print(f"    Updated lead {len(to_update)} of {len(to_update)} ({to_update[-1]}) in {time.time() - lead_start:.1f}s")
    qa.record("INFO", f"Time to update {len(to_update)} leads: {time.time() - started:.0f} seconds.")
    qa.record("PASS", f"Step 3: the last update was saved. {len(to_update)} leads are updated.")

    shown_count = disposition_shown(qa, to_update)
    print(f"    Call Disposition '{DISPOSITION}' shown for {shown_count} of {len(to_update)} leads")

    # The new batch: right after the update, then after a refresh, then after a new log in
    found = set()
    where = "right after the last update"
    end = time.time() + 10
    while True:
        found = new_leads(qa, before_ids)
        if found or time.time() > end:
            break
        time.sleep(1)

    if not found:
        where = "after refreshing the page"
        qa.driver.refresh()
        time.sleep(2)
        if qa.logged_out():
            qa.login(EMAIL, PASSWORD)
        found = new_leads(qa, before_ids)

    if not found:
        where = "after logging in again"
        qa.logout()
        qa.login(EMAIL, PASSWORD)
        found = new_leads(qa, before_ids)

    qa.shot("3_new_batch")
    print(f"    New leads found: {len(found)} ({where})")

    if len(found) == NEW_BATCH:
        qa.record("PASS", f"Step 4: the system distributed a new batch of {NEW_BATCH} undistributed leads ({where}).")
    elif found:
        qa.record(
            "FAIL",
            f"Step 4: expected a new batch of {NEW_BATCH} undistributed leads. "
            f"Actual: {len(found)} new leads were distributed ({where}).",
        )
    else:
        qa.record(
            "FAIL",
            f"Step 4: expected a new batch of {NEW_BATCH} undistributed leads. Actual: no new leads, "
            "not right after the update, not after a refresh and not after logging in again. "
            "(Also check that undistributed leads are left in the system.)",
        )


qa = QA("TC-LDS-11", "Telemarketer Module - Update 10 Leads x Distribution", "WEB-5", WEBSITE, HEADLESS)
qa.execute(test)
