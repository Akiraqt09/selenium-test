"""
qa_helpers.py - shared helpers for the TC-LDS Selenium scripts.

Keep this file in the SAME folder as the tc_lds_*.py scripts.
It contains NO passwords. Each script holds only the test account it needs.

Result labels used by the scripts:
  [PASS]  the system behaved as expected
  [FAIL]  the system did NOT behave as expected (a product defect)
  [ERROR] the script could not continue (a script/page problem, not a result)
  [SKIP]  a step was not run (blocked by an earlier failure, or switched off)
  [INFO]  extra information
"""

import re
import sys
import time
import traceback

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# The sidebar of the system has some typographical errors (reported as defects).
# Both the correct and the misspelled labels are accepted so the scripts keep
# working after the typos are fixed.
DASHBOARD_LABELS = ("Dashboard",)
LEADS_LABELS = ("Leads", "Leeds")
ADD_LEAD_LABELS = ("Add New Lead", "Add New Leed")
EMAILS_LABELS = ("Emails", "Emaiils")
USERS_LABELS = ("Users",)
ADD_USER_LABELS = ("Add New User",)
SIGN_OUT_LABELS = ("Sign Out", "Sigm Out")

LOWER = "abcdefghijklmnopqrstuvwxyz"
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def text_equals_any(labels):
    """XPath condition: the element text equals one of the labels."""
    return " or ".join(f"normalize-space()='{label}'" for label in labels)


def text_contains_ci(text):
    """XPath condition: the element text contains `text` (ignoring case)."""
    return (
        f"contains(translate(normalize-space(), '{UPPER}', '{LOWER}'), '{text.lower()}')"
    )


class QA:
    def __init__(self, tc_id, title, jira, website, headless=True):
        self.tc_id = tc_id
        self.title = title
        self.jira = jira
        self.website = website
        self.prefix = tc_id.lower().replace("-", "_")
        self.results = []
        self.current = "starting"

        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 60)

        print()
        print("==========================================")
        print(f"{tc_id}: {title} (Jira {jira})")
        print(f"Website: {website}")
        print("==========================================")

    # ------------------------------------------------------------------
    # recording
    # ------------------------------------------------------------------
    def step(self, text):
        self.current = text
        print(f"\n--- {text} ---")

    def record(self, status, text):
        self.results.append((status, text))
        print(f"[{status}] {text}")

    def shot(self, name):
        file_name = f"{self.prefix}_{name}.png"
        self.driver.save_screenshot(file_name)
        print(f"    (screenshot saved: {file_name})")

    # ------------------------------------------------------------------
    # basic actions
    # ------------------------------------------------------------------
    def click(self, element):
        try:
            element.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", element)

    def visible(self, xpath, seconds=10):
        """The first visible element for the XPath, or None."""
        try:
            return WebDriverWait(self.driver, seconds).until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            )
        except TimeoutException:
            return None

    def any_visible(self, xpath):
        for element in self.driver.find_elements(By.XPATH, xpath):
            if element.is_displayed():
                return element
        return None

    def clear_text(self, element):
        element.click()
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.BACKSPACE)

    # ------------------------------------------------------------------
    # login / logout / menu
    # ------------------------------------------------------------------
    def login(self, email, password):
        driver = self.driver
        if not driver.find_elements(By.CSS_SELECTOR, 'input[type="email"]'):
            driver.get(self.website)
        email_field = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))
        )
        email_field.clear()
        email_field.send_keys(email)
        password_field = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
        password_field.clear()
        password_field.send_keys(password)
        self.click(
            self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Log In']"))
            )
        )
        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//*[normalize-space()='DASHBOARD']"))
        )
        time.sleep(2)

    def logged_out(self):
        """True if the login form is showing."""
        return bool(
            [
                e
                for e in self.driver.find_elements(By.CSS_SELECTOR, 'input[type="password"]')
                if e.is_displayed()
            ]
        )

    def menu(self, labels, seconds=30):
        """The sidebar item with one of the labels."""
        condition = text_equals_any(labels)
        li_xpath = f"//li[contains(@class,'ps-menuitem-root')][.//*[{condition}]]"
        plain_xpath = f"//*[{condition}]"
        end = time.time() + seconds
        while time.time() < end:
            for xpath in (li_xpath, plain_xpath):
                element = self.any_visible(xpath)
                if element is not None:
                    return element
            time.sleep(0.5)
        raise TimeoutException(f"Sidebar item not found: {labels}")

    def open_menu(self, labels, wait_seconds=3):
        self.click(self.menu(labels))
        time.sleep(wait_seconds)

    def logout(self):
        driver = self.driver
        try:
            self.click(self.menu(SIGN_OUT_LABELS, seconds=10))
            time.sleep(1)
            confirm = self.any_visible(
                "//button[normalize-space()='Yes' or normalize-space()='Confirm' "
                "or normalize-space()='OK' or normalize-space()='Sign Out' "
                "or normalize-space()='Sigm Out']"
            )
            if confirm is not None:
                self.click(confirm)
            WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))
            )
        except Exception:
            print("    (sign out did not work, clearing the session instead)")
            driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
            driver.delete_all_cookies()
            driver.get(self.website)
            self.wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))
            )

    # ------------------------------------------------------------------
    # MUI dropdowns (Select)
    # ------------------------------------------------------------------
    def choose_option(self, combobox, text):
        self.click(combobox)
        option_xpath = (
            f"//li[@role='option'][normalize-space()='{text}' or @data-value='{text}']"
        )
        option = self.visible(option_xpath, seconds=15)
        if option is None:
            names = [
                o.text for o in self.driver.find_elements(By.CSS_SELECTOR, 'li[role="option"]')
            ]
            print("    Option not found. Options in the dropdown:", names)
            raise TimeoutException(f"Dropdown option not found: {text}")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option)
        self.click(option)
        time.sleep(0.5)

    # ------------------------------------------------------------------
    # data grid (Assigned Leads, Leads, Users)
    # ------------------------------------------------------------------
    def grid_rows(self):
        rows = self.driver.find_elements(By.CSS_SELECTOR, "[role='row']")
        return [
            row
            for row in rows
            if row.is_displayed() and not row.find_elements(By.CSS_SELECTOR, "[role='columnheader']")
        ]

    def wait_for_rows(self, seconds=20):
        end = time.time() + seconds
        while time.time() < end:
            rows = self.grid_rows()
            if rows:
                return rows
            time.sleep(1)
        return []

    def grid_total(self):
        """The total from the footer (for example '1-10 of 10'), or None."""
        for selector in (".MuiTablePagination-displayedRows", "[class*='displayedRows']"):
            for element in self.driver.find_elements(By.CSS_SELECTOR, selector):
                match = re.search(r"of\s+(\d+)", element.text)
                if match:
                    return int(match.group(1))
        return None

    def grid_headers(self):
        headers = {}
        for header in self.driver.find_elements(By.CSS_SELECTOR, "[role='columnheader']"):
            index = header.get_attribute("aria-colindex")
            headers[index] = header.text.strip() or (header.get_attribute("aria-label") or "")
        return headers

    def row_id(self, row):
        value = row.get_attribute("data-id")
        if value:
            return value
        cells = row.find_elements(By.CSS_SELECTOR, "[role='gridcell']")
        for cell in cells:
            if cell.text.strip():
                return cell.text.strip()
        return row.text.strip()

    def row_values(self, row):
        headers = self.grid_headers()
        values = {}
        for cell in row.find_elements(By.CSS_SELECTOR, "[role='gridcell']"):
            index = cell.get_attribute("aria-colindex")
            values[headers.get(index) or f"col{index}"] = cell.text.strip()
        return values

    def find_row(self, row_id):
        for row in self.grid_rows():
            if self.row_id(row) == row_id:
                return row
        return None

    def scroll_grid(self, right=True):
        """Scroll the data grid sideways (columns outside the view are not drawn)."""
        self.driver.execute_script(
            "var s = document.querySelector('.MuiDataGrid-virtualScroller');"
            "if (s) { s.scrollLeft = arguments[0] ? s.scrollWidth : 0; }",
            right,
        )
        time.sleep(1)

    def action_cell(self, row):
        cells = row.find_elements(By.CSS_SELECTOR, "[data-field='actions'], [data-field='action']")
        if cells:
            return cells[0]
        cells = row.find_elements(By.CSS_SELECTOR, "[role='gridcell']")
        return cells[-1] if cells else row

    def clickable(self, icon):
        """The button/link around an icon, or the icon itself."""
        parents = icon.find_elements(
            By.XPATH, "./ancestor::*[self::button or self::a or @role='button'][1]"
        )
        return parents[0] if parents else icon

    def row_action(self, row, test_ids, position):
        """An action icon of the row (eye, edit, call, email).

        Looks for the icon by its test id first, then by its position among the
        icons of the Actions column (0 = eye, 1 = edit, 2 = call, 3 = email).
        """
        row_key = row.get_attribute("data-id")
        cell = None
        for attempt in range(2):
            if attempt == 1:
                self.scroll_grid(right=True)  # the Actions column may be out of view
                if row_key:
                    again = self.driver.find_elements(
                        By.CSS_SELECTOR, f"[role='row'][data-id='{row_key}']"
                    )
                    if again:
                        row = again[0]
            for test_id in test_ids:
                icons = row.find_elements(By.CSS_SELECTOR, f'svg[data-testid="{test_id}"]')
                if icons:
                    return self.clickable(icons[0])
            cell = self.action_cell(row)
            icons = cell.find_elements(By.CSS_SELECTOR, "svg")
            if len(icons) > position:
                return self.clickable(icons[position])

        html = (cell.get_attribute("outerHTML") if cell is not None else "") or ""
        print("    Action icon not found. HTML of the Actions cell (send this to fix the script):")
        print("    " + html[:1500])
        raise TimeoutException(f"Action icon not found in the row ({test_ids})")

    # ------------------------------------------------------------------
    # warnings shown by the system
    # ------------------------------------------------------------------
    def warning_text(self):
        """The warning shown when the system refuses a form (or '')."""
        message = self.driver.execute_script(
            "var f = document.querySelector(':invalid'); return f ? f.validationMessage : '';"
        )
        if message:
            return message
        element = self.any_visible(
            f"//*[{text_contains_ci('please fill')} or {text_contains_ci('is required')} "
            f"or {text_contains_ci('required field')}]"
        )
        if element is not None and len(element.text) < 120:
            return element.text.strip()
        for selector in (".MuiFormHelperText-root.Mui-error", '[role="alert"]'):
            for found in self.driver.find_elements(By.CSS_SELECTOR, selector):
                if found.is_displayed() and found.text.strip():
                    return found.text.strip()
        return ""

    # ------------------------------------------------------------------
    # run + summary
    # ------------------------------------------------------------------
    def execute(self, test):
        try:
            test(self)
        except TimeoutException as error:
            self.record(
                "ERROR",
                f"The script stopped at: {self.current} (an element did not appear in time"
                f"{': ' + str(error.msg) if error.msg else ''}).",
            )
            print("    Current URL:", self.driver.current_url)
            traceback.print_exc()
            self.shot("error")
        except Exception as error:
            self.record(
                "ERROR",
                f"The script stopped at: {self.current} ({type(error).__name__}: {error})",
            )
            traceback.print_exc()
            try:
                self.shot("error")
            except Exception:
                pass
        finally:
            self.driver.quit()
        self.finish()

    def finish(self):
        has_error = any(status == "ERROR" for status, _ in self.results)
        failed = [text for status, text in self.results if status == "FAIL"]

        print()
        print("==========================================")
        print(f"{self.tc_id} SUMMARY")
        print("------------------------------------------")
        for status, text in self.results:
            print(f"[{status}] {text}")
        print("------------------------------------------")
        if has_error:
            print("RESULT: INCOMPLETE - the script could not finish, so this is not a test result.")
        elif failed:
            print(f"RESULT: FAILED - {len(failed)} check(s) failed (matches defect {self.jira}).")
        else:
            print("RESULT: PASSED - every check matched the expected result.")
        print("==========================================")
        sys.exit(1 if (has_error or failed) else 0)

