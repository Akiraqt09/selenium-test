"""TC-LDS-08 – Verify automatic distribution of 10 leads at telemarketer login."""
from selenium_helpers import *

def test(driver):
    login(driver, "TELEMARKETER")
    screenshot(driver, "TC-LDS-08_after_login")
    nav_to(driver, "Assigned Leads", "Assigned Lead", "My Leads")
    wait(driver).until(lambda d: len(visible_rows(d)) > 0 or "no leads" in visible_text(d).lower())
    rows = visible_rows(driver)
    count = len(rows)
    print(f"[OBSERVED] Visible assigned lead rows: {count}")
    if count != 10:
        raise TestFailure(f"Expected exactly 10 assigned leads after login; observed {count}.")
    screenshot(driver, "TC-LDS-08_assigned_leads")
    print("[CHECK] Assigned Leads list contains exactly 10 visible lead rows.")

if __name__ == "__main__":
    run_case("TC-LDS-08", test)
