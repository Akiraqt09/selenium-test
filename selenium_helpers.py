"""Shared Selenium utilities for SortR Lead Distribution test cases."""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    ElementClickInterceptedException, StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://sortrleaddistribution-client.onrender.com/").rstrip("/") + "/"
WAIT_SECONDS = int(os.getenv("WAIT_SECONDS", "18"))
ROOT = Path(__file__).resolve().parent
SCREENSHOT_DIR = ROOT / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

class TestBlocked(RuntimeError):
    """The test could not safely proceed; this is not a pass."""

class TestFailure(AssertionError):
    """An expected UI behavior was not observed."""

def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "y"}

def make_driver():
    mode = os.getenv("BROWSER_MODE", "auto").lower()
    in_codespaces = bool(os.getenv("CODESPACES") or os.getenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN"))
    headless = mode == "headless" or (mode == "auto" and in_codespaces)

    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    binary = os.getenv("CHROME_BIN")
    if binary:
        options.binary_location = binary

    # Selenium 4.6+ Selenium Manager resolves the matching driver.
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(0)
    print(f"[INFO] Browser mode: {'HEADLESS' if headless else 'HEADED'}")
    print(f"[INFO] Browser: {driver.capabilities.get('browserName')} {driver.capabilities.get('browserVersion')}")
    return driver

def wait(driver, seconds=WAIT_SECONDS):
    return WebDriverWait(driver, seconds, ignored_exceptions=(StaleElementReferenceException,))

def visible_text(driver) -> str:
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        return ""

def screenshot(driver, label: str):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", label)
    path = SCREENSHOT_DIR / f"{stamp}_{safe}.png"
    try:
        driver.save_screenshot(str(path))
        print(f"[EVIDENCE] {path}")
    except WebDriverException as exc:
        print(f"[WARN] Could not save screenshot: {exc}")
    return path

def find_by_text(driver, text: str, tags=("button", "a", "[role='button']"), exact=False):
    for tag in tags:
        xpath = f"//{tag}[contains(normalize-space(.), {xpath_literal(text)})]"
        if exact:
            xpath = f"//{tag}[normalize-space(.)={xpath_literal(text)}]"
        for el in driver.find_elements(By.XPATH, xpath):
            if el.is_displayed():
                return el
    return None

def xpath_literal(value: str) -> str:
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    return "concat(" + ', "\'", '.join("'" + p + "'" for p in parts) + ")"

def click_text(driver, text: str, required=True):
    el = find_by_text(driver, text)
    if not el:
        if required:
            raise TestFailure(f"Could not find a visible button/link containing text: {text!r}")
        return None
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    try:
        el.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", el)
    return el

def find_input(driver, labels=(), placeholders=(), names=(), input_types=(), index=None):
    candidates = []
    for label in labels:
        candidates.extend(driver.find_elements(By.XPATH,
            f"//label[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
            f"{xpath_literal(label.lower())})]"))
    for lab in candidates:
        try:
            target = lab.find_element(By.XPATH, ".//input | .//textarea | .//select")
            if target.is_displayed() and target.is_enabled():
                return target
        except NoSuchElementException:
            pass
        for attr in ("for",):
            key = lab.get_attribute(attr)
            if key:
                found = driver.find_elements(By.ID, key)
                if found and found[0].is_displayed():
                    return found[0]

    for placeholder in placeholders:
        els = driver.find_elements(By.XPATH,
            f"//*[@placeholder and contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
            f"{xpath_literal(placeholder.lower())})]")
        for el in els:
            if el.is_displayed() and el.is_enabled():
                return el
    for name in names:
        for by, val in ((By.NAME, name), (By.ID, name)):
            for el in driver.find_elements(by, val):
                if el.is_displayed() and el.is_enabled():
                    return el
    for typ in input_types:
        for el in driver.find_elements(By.CSS_SELECTOR, f"input[type='{typ}']"):
            if el.is_displayed() and el.is_enabled():
                return el
    if index is not None:
        els = [e for e in driver.find_elements(By.CSS_SELECTOR, "input,textarea")
               if e.is_displayed() and e.is_enabled()]
        if len(els) > index:
            return els[index]
    return None

def fill(el, value: str):
    el.click()
    el.send_keys(Keys.CONTROL, "a")
    el.send_keys(value)

def require_input(driver, description, **kwargs):
    el = find_input(driver, **kwargs)
    if not el:
        raise TestFailure(f"Could not locate the {description} field. Inspect the screenshot/DOM and update locator hints.")
    return el

def login(driver, role: str):
    role = role.upper()
    if role == "TELEMARKETER":
        email, password = os.getenv("TELEMARKETER_EMAIL"), os.getenv("TELEMARKETER_PASSWORD")
    elif role == "LEAD_GENERATION":
        email, password = os.getenv("LEAD_GENERATION_EMAIL"), os.getenv("LEAD_GENERATION_PASSWORD")
    elif role == "TEAM_LEAD":
        email, password = os.getenv("TEAM_LEAD_EMAIL"), os.getenv("TEAM_LEAD_PASSWORD")
    else:
        raise ValueError(f"Unsupported role: {role}")

    if not email or not password:
        raise TestBlocked(f"Missing credentials for {role}. Configure the matching environment variables in .env.")

    driver.get(BASE_URL)
    wait(driver).until(lambda d: d.execute_script("return document.readyState") == "complete")
    email_el = require_input(driver, "login email", labels=("email",), placeholders=("email",), names=("email",), input_types=("email",), index=0)
    pass_el = require_input(driver, "login password", labels=("password",), placeholders=("password",), names=("password",), input_types=("password",), index=1)
    fill(email_el, email)
    fill(pass_el, password)
    click_text(driver, "Log In")
    wait(driver).until(lambda d: "login" not in d.current_url.lower() or
                       any(x in visible_text(d).lower() for x in ("invalid", "incorrect", "error")))
    time.sleep(1.2)
    body = visible_text(driver).lower()
    if any(msg in body for msg in ("invalid credentials", "incorrect password", "account not found")):
        raise TestFailure(f"{role} login was rejected: {body[:300]}")
    print(f"[INFO] Logged in as configured role: {role}")

def nav_to(driver, *labels):
    for label in labels:
        el = find_by_text(driver, label, tags=("a", "button", "[role='button']", "li"))
        if el:
            try:
                el.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", el)
            time.sleep(1)
            return
    raise TestFailure(f"Could not locate navigation item. Tried: {labels}")

def visible_rows(driver):
    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    return [r for r in rows if r.is_displayed() and r.text.strip()]

def first_action_in_row(row, keywords):
    # Prefer explicit accessible labels/titles, then inspect icon markup used by common UI kits.
    for key in keywords:
        for el in row.find_elements(By.XPATH, f".//*[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),{xpath_literal(key.lower())}) or contains(translate(@title,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),{xpath_literal(key.lower())})]"):
            if el.is_displayed():
                return el
        for el in row.find_elements(By.XPATH, f".//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),{xpath_literal(key.lower())})]"):
            if el.is_displayed():
                return el
    tokens = {
        "email": ("mail", "envelope", "email"),
        "mail": ("mail", "envelope", "email"),
        "send email": ("mail", "envelope", "email"),
        "call": ("phone", "call", "dial"),
        "phone": ("phone", "call", "dial"),
        "dial": ("phone", "call", "dial"),
        "edit": ("edit", "pencil", "pen"),
        "update": ("edit", "pencil", "pen"),
    }
    wanted = tuple(t for k in keywords for t in tokens.get(k.lower(), (k.lower(),)))
    for el in row.find_elements(By.CSS_SELECTOR, "button, a, [role='button']"):
        if not el.is_displayed():
            continue
        markup = (el.get_attribute("outerHTML") or "").lower()
        if any(token in markup for token in wanted):
            return el
    return None

def find_select(driver, labels=(), names=()):
    for label in labels:
        for lab in driver.find_elements(By.XPATH,
            f"//label[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),{xpath_literal(label.lower())})]"):
            try:
                el = lab.find_element(By.XPATH, ".//select")
                if el.is_displayed() and el.is_enabled():
                    return el
            except NoSuchElementException:
                key = lab.get_attribute("for")
                if key:
                    for el in driver.find_elements(By.ID, key):
                        if el.tag_name.lower() == "select" and el.is_displayed():
                            return el
    for name in names:
        for by, val in ((By.NAME, name), (By.ID, name)):
            for el in driver.find_elements(by, val):
                if el.tag_name.lower() == "select" and el.is_displayed():
                    return el
    return None

def run_case(case_id: str, test_function):
    driver = None
    status = "ERROR"
    try:
        print(f"\n===== {case_id} START =====")
        driver = make_driver()
        test_function(driver)
        status = "PASS"
        print(f"[{status}] {case_id}")
    except TestBlocked as exc:
        status = "BLOCKED"
        print(f"[{status}] {case_id}: {exc}")
    except (TestFailure, AssertionError, TimeoutException, NoSuchElementException) as exc:
        status = "FAIL"
        print(f"[{status}] {case_id}: {exc}")
        if driver:
            screenshot(driver, f"{case_id}_FAIL")
    except Exception as exc:
        status = "ERROR"
        print(f"[{status}] {case_id}: {type(exc).__name__}: {exc}")
        if driver:
            screenshot(driver, f"{case_id}_ERROR")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        print(f"===== {case_id} RESULT: {status} =====\n")
    if status in {"FAIL", "ERROR"}:
        sys.exit(1)
    if status == "BLOCKED":
        sys.exit(2)
