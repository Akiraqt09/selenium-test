"""
TC-LDS-10 | Telemarketer Module - Update Lead with Empty Required Fields | Jira: WEB-4

The system must NOT save an updated lead when a required field is emptied,
and the lead's original information must stay unchanged.

For each step the script opens the Update Lead form of the first assigned
lead, empties ONE field (the last step empties ALL of them), clicks Update,
then checks the lead in the Assigned Leads list:

  the lead's information is unchanged  -> [PASS]  (the update was blocked)
  the lead's information changed       -> [FAIL]  (the update was saved)

Steps (same as the test case in the spreadsheet):
  2. Lead Name     5. Street Address   8. Email Address   11. ALL fields
  3. Type          6. City             9. Call Disposition
  4. Phone Number  7. Postcode        10. Remarks

The Type and Call Disposition dropdowns have no really empty choice, so they
are "emptied" by choosing "Choose One".

If a step wrongly SAVES an empty value, the script tries to put the old value
back (text fields only). Check the lead afterwards.

The form fields are found by their ORDER on the page (Lead Name, Type, Phone
Number, Street Address, City, Postcode, Email Address, Call Disposition,
Remarks). The script prints what it found so you can check this order.
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
HEADLESS = False  # False = show the browser window (on a computer)

# Telemarketer test account
EMAIL = "emmandc0908@gmail.com"
PASSWORD = "ABCabc123"

FIELDS = [
    "Lead Name",
    "Type",
    "Phone Number",
    "Street Address",
    "City",
    "Postcode",
    "Email Address",
    "Call Disposition",
    "Remarks",
]
STEPS = [
    (2, "Lead Name", [0]),
    (3, "Type", [1]),
    (4, "Phone Number", [2]),
    (5, "Street Address", [3]),
    (6, "City", [4]),
    (7, "Postcode", [5]),
    (8, "Email Address", [6]),
    (9, "Call Disposition", [7]),
    (10, "Remarks", [8]),
    (11, "ALL fields", list(range(9))),
]

# Columns that change by themselves (time stamps, buttons) are not compared.
IGNORED_COLUMNS = ("distribut", "updated", "action")

CONTROL_SELECTOR = (
    'input:not([type="hidden"]):not([type="checkbox"]):not([aria-hidden="true"])'
    ":not(.MuiSelect-nativeInput), "
    'textarea:not([aria-hidden="true"]), [role="combobox"]'
)


# ==========================================
# HELPERS
# ==========================================


def data_values(qa, row):
    values = qa.row_values(row)
    return {
        name: text
        for name, text in values.items()
        if not any(word in name.lower() for word in IGNORED_COLUMNS)
    }


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


def is_dropdown(element):
    return element.get_attribute("role") == "combobox"


def value_of(element):
    return (element.get_attribute("value") or element.text or "").strip()


def describe(element):
    return (
        f"{element.tag_name} name={element.get_attribute('name')!r} "
        f"placeholder={element.get_attribute('placeholder')!r} value={value_of(element)!r}"
    )


def open_edit_form(qa, lead_id):
    """Open the Assigned Leads page, then the Update Lead form of the lead.
    Returns the lead's values from the list (before the update)."""
    qa.close_dialogs()
    qa.open_menu(LEADS_LABELS)
    qa.wait_for_rows()
    row = qa.find_row(lead_id)
    if row is None:
        raise TimeoutException("the lead was not found in the Assigned Leads list")
    before = data_values(qa, row)
    qa.click(qa.row_action(row, ("EditIcon", "ModeEditIcon", "EditOutlinedIcon"), 1))
    if qa.visible("//button[normalize-space()='Update']", 20) is None:
        raise TimeoutException("the Update Lead form did not open")
    time.sleep(1)
    return before


def clear_control(qa, element):
    """True if the field was emptied."""
    if is_dropdown(element):
        qa.click(element)
        time.sleep(1)
        # The dropdowns have no really empty choice: "Choose One" is the way to
        # leave Type / Call Disposition empty. The list is scrolled, so the
        # option must be found without needing to be "visible" first.
        options = qa.driver.find_elements(
            By.XPATH,
            "//li[@role='option'][@data-value='' "
            "or translate(normalize-space(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz')='choose one']",
        )
        if not options:
            names = [o.text for o in qa.driver.find_elements(By.CSS_SELECTOR, 'li[role="option"]')]
            print("    No 'Choose One' option. Options in the dropdown:", names)
            qa.close_dialogs()
            return False
        qa.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", options[0])
        time.sleep(0.5)
        qa.driver.execute_script("arguments[0].click();", options[0])
        time.sleep(1)
        return True
    qa.clear_text(element)
    return True


def dismiss_popup(qa):
    button = qa.any_visible(
        "//*[@role='dialog']//button[normalize-space()='OK' or normalize-space()='Close' "
        "or normalize-space()='Okay' or normalize-space()='Continue']"
    )
    if button is not None:
        qa.click(button)
        time.sleep(1)


def restore(qa, lead_id, indexes, originals):
    """Best effort: put the old text back after a wrong save."""
    try:
        open_edit_form(qa, lead_id)
        controls = form_controls(qa)
        for index in indexes:
            if index < len(controls) and not is_dropdown(controls[index]) and originals[index]:
                qa.clear_text(controls[index])
                controls[index].send_keys(originals[index])
        qa.click(qa.visible("//button[normalize-space()='Update']", 10))
        time.sleep(3)
        dismiss_popup(qa)
        print("    (tried to put the old value back)")
    except Exception as error:
        print("    (could not put the old value back:", error, ")")


# ==========================================
# TEST
# ==========================================


def test(qa):
    qa.step("Precondition - log in as a Telemarketer")
    qa.login(EMAIL, PASSWORD)
    qa.record("PASS", "Precondition: logged in as a Telemarketer.")

    qa.step("Step 1 - click 'Leads' and the edit icon of an assigned lead")
    qa.open_menu(LEADS_LABELS)
    rows = qa.wait_for_rows()
    if not rows:
        raise TimeoutException("no assigned lead is listed (the test needs at least one)")
    lead_id = qa.row_id(rows[0])
    print(f"    Lead used in this test: {lead_id}")

    open_edit_form(qa, lead_id)
    controls = form_controls(qa)
    print(f"    Form fields found: {len(controls)}")
    for number, control in enumerate(controls):
        name = FIELDS[number] if number < len(FIELDS) else "?"
        print(f"      {number + 1}. {name}: {describe(control)}")
    qa.shot("1_update_form")
    if len(controls) != len(FIELDS):
        raise TimeoutException(
            f"expected {len(FIELDS)} form fields but found {len(controls)} - "
            "send the printed list above so the script can be adjusted"
        )
    qa.record("PASS", "Step 1: the Update Lead form is displayed with the lead's current information.")

    for step, label, indexes in STEPS:
        qa.step(f"Step {step} - clear {label} and click Update")
        before = open_edit_form(qa, lead_id)
        controls = form_controls(qa)
        originals = [value_of(control) for control in controls]

        cleared = [clear_control(qa, controls[i]) for i in indexes]
        if not all(cleared):
            qa.record("SKIP", f"Step {step}: {label} could not be emptied (no \"Choose One\" option found in the dropdown).")
            continue

        qa.click(qa.visible("//button[normalize-space()='Update']", 10))
        time.sleep(3)
        warning = qa.warning_text()
        qa.shot(f"step{step}")
        dismiss_popup(qa)
        qa.close_dialogs()

        qa.open_menu(LEADS_LABELS)
        qa.wait_for_rows()
        row = qa.find_row(lead_id)
        after = data_values(qa, row) if row is not None else {}
        changed = {
            name: (before[name], after.get(name, ""))
            for name in before
            if before[name] != after.get(name, "")
        }

        if changed:
            detail = "; ".join(f"{name}: '{old}' -> '{new}'" for name, (old, new) in changed.items())
            qa.record(
                "FAIL",
                f"Step {step}: {label} emptied -> the update was SAVED ({detail}). "
                "Expected: blocked with a validation message, original information unchanged.",
            )
            restore(qa, lead_id, indexes, originals)
        else:
            shown = f'validation message: "{warning}"' if warning else "no validation text found"
            qa.record(
                "PASS",
                f"Step {step}: {label} emptied -> the update was blocked, the lead is unchanged ({shown}).",
            )


qa = QA("TC-LDS-10", "Telemarketer Module - Update Lead with Empty Required Fields", "WEB-4", WEBSITE, HEADLESS)
qa.execute(test)
