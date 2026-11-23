# SortR Lead Distribution – Selenium test scripts

Six test scripts are included: TC-LDS-08, 11, 12, 13, 14 and 17.

## Important test-safety notes

These scripts target the URL configured in `.env`. Use only an environment and records you are authorized to test.

- TC-LDS-08 and TC-LDS-14 are primarily read-only.
- TC-LDS-11 changes lead records. It stops before editing unless `ALLOW_DATA_MUTATION=1`.
- TC-LDS-12 may send a real email. It will not click Send unless `ALLOW_EMAIL_SEND=1`.
- TC-LDS-13 submits an empty email form to verify validation.
- TC-LDS-17 creates a user. It stops before creation unless `ALLOW_DATA_MUTATION=1`.

The supplied project report identifies the historical defects:
- TC-LDS-08: 8 leads were distributed instead of 10.
- TC-LDS-11: only 8 leads were distributed after the current batch was updated.
- TC-LDS-12/13: the email icon logged the telemarketer out instead of opening Send An Email.
- TC-LDS-14: Microsip showed “Invalid Number”.
- TC-LDS-17: Add New User redirected to Leads and did not create the user.

The document screenshots on printed pages 20–25 describe the intended workflows. The scripts use accessible labels, placeholders and visible text where possible. The uploaded case screenshots specify the sample disposition `Warm Lead`, a template-based email subject and message, and a Team Leader-created Telemarketer account. If the live application uses different labels/markup, update `selenium_helpers.py`. They deliberately fail with a diagnostic rather than silently claiming success.

## Setup – Windows / Visual Studio Code

1. Install Python 3.10+ and Google Chrome.
2. Open this folder in VS Code.
3. Create a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and fill in the account credentials.
5. Run one script:

   ```powershell
   python tc_lds_08.py
   ```

   On Windows, `BROWSER_MODE=auto` opens visible Chrome. Use `BROWSER_MODE=headless` to hide it.

## Setup – GitHub Codespaces

1. Add the needed account values as Codespaces repository secrets or environment variables. Do not commit `.env`.
2. In the Codespaces terminal:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Ensure Google Chrome is installed in the Codespace. Selenium Manager can manage the matching driver when network access permits. If Chrome is installed at a nonstandard path, set `CHROME_BIN`.
4. Run:

   ```bash
   BROWSER_MODE=headless python tc_lds_08.py
   ```

The scripts set headless Chrome options and do not require a visible desktop. They use `--headless=new`, not a `chromium` command. If your Codespace image only has Chromium, set `CHROME_BIN` to its actual executable path.

## Credentials

The scripts use these environment variables:
- `TELEMARKETER_EMAIL`, `TELEMARKETER_PASSWORD`
- `LEAD_GENERATION_EMAIL`, `LEAD_GENERATION_PASSWORD`
- `TEAM_LEAD_EMAIL`, `TEAM_LEAD_PASSWORD`

Never paste passwords into Python files or commit them to GitHub.

## Running all cases

Run each file separately so the output and screenshots remain attributable to the case:

```bash
python tc_lds_08.py
python tc_lds_11.py
python tc_lds_12.py
python tc_lds_13.py
python tc_lds_14.py
python tc_lds_17.py
```

Screenshots and logs are saved under `screenshots/`. A `PASS` means the expected behavior was observed. A `FAIL` means the observed behavior did not match the expected result. A `BLOCKED` result means a safety switch or missing test data prevented a destructive step; it is not a pass.

## Important limitations

I reviewed the uploaded QA project document, including its test-case screenshots and recorded observations. The document does not provide the current live DOM selectors or a dedicated test-data sheet. The live application also needs a real browser session to verify its current markup. Therefore these scripts use resilient label/text-based locators and clear failure diagnostics, but the first run may reveal selectors that need to be aligned with the current UI. Do not treat the scripts as validated against the live site until you run them and review the output/screenshots.
