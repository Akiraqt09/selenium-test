"""
TC-LDS-14 | Telemarketer Module - Call Button | Jira: WEB-8

The Call button of a lead must open the Microsip dial pad with the lead's
phone number.

Steps (same as the test case in the spreadsheet):
  1. Click "Leads" -> the Assigned Leads page is displayed
  2. Click the call (phone) icon of a lead -> the system redirects to Microsip
  3. Verify the number on the Microsip -> the dial pad shows the pre-filled
     phone number that matches the selected lead

Known defect (WEB-8): Microsip shows "Invalid Number" instead of the number.

IMPORTANT: Selenium can only see the browser, not the Microsip program. So
this script checks the call link of EVERY lead on the page instead:
  - it uses the "callto:" protocol
  - the number in the link matches the lead's phone number in the list
  - the number can be dialed (only digits, with an optional + at the start,
    no spaces, dashes or other characters)
A link like "callto:61 2 6921 3368" (with spaces) is a likely reason for
"Invalid Number". What Microsip really shows still has to be checked by eye.
"""

import re
from urllib.parse import unquote

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
PASSWORD = "ABCabc123!"

CALL_LINK = 'a[aria-label="Call lead with MicroSIP"]'


def digits(text):
    return re.sub(r"\D", "", text or "")


def test(qa):
    qa.step("Precondition - log in as a Telemarketer")
    qa.login(EMAIL, PASSWORD)
    qa.record("PASS", "Precondition: logged in as a Telemarketer.")

    # ---- Step 1 ----
    qa.step("Step 1 - click 'Leads' in the sidebar")
    qa.open_menu(LEADS_LABELS)
    rows = qa.wait_for_rows()
    if not rows:
        raise TimeoutException("no assigned lead is listed (the test needs at least one)")
    qa.shot("1_assigned_leads")
    qa.record("PASS", f"Step 1: the Assigned Leads page is displayed ({len(rows)} leads on the page).")

    # ---- Steps 2 and 3 ----
    qa.step("Steps 2-3 - check the call link of every lead")
    problems = []
    checked = 0
    for row in rows:
        values = qa.row_values(row)
        name = next((text for key, text in values.items() if "name" in key.lower() or "neme" in key.lower()), "?")
        phone = next((text for key, text in values.items() if key.lower().startswith("phone")), "")

        links = row.find_elements(By.CSS_SELECTOR, CALL_LINK)
        if not links:
            problems.append(f"{name}: no call link found")
            continue
        href = links[0].get_attribute("href") or ""
        checked += 1
        number = unquote(href.split(":", 1)[1]) if ":" in href else ""
        print(f"    {name}: phone in list = {phone!r}, call link = {href!r}")

        if not href.lower().startswith("callto:"):
            problems.append(f"{name}: the link does not use callto ({href})")
        elif not phone:
            problems.append(f"{name}: the lead has no phone number but a call link exists ({href})")
        elif digits(number) != digits(phone):
            problems.append(f"{name}: the link number does not match the lead's phone ({href} vs {phone})")
        elif not re.fullmatch(r"\+?\d+", number):
            problems.append(f"{name}: the number can not be dialed because of spaces or symbols ({href})")

    qa.shot("2_call_links")
    if problems:
        shown = "; ".join(problems[:3]) + ("; ..." if len(problems) > 3 else "")
        qa.record(
            "FAIL",
            f"Steps 2-3: {len(problems)} of {len(rows)} call links are not correct. "
            f"Expected the link to hold the lead's phone number as a dialable number. Actual: {shown}",
        )
    else:
        qa.record(
            "PASS",
            f"Steps 2-3: all {checked} call links hold the lead's dialable phone number. "
            "Check Microsip by eye - it can not be seen by Selenium.",
        )


qa = QA("TC-LDS-14", "Telemarketer Module - Call Button", "WEB-8", WEBSITE, HEADLESS)
qa.execute(test)
