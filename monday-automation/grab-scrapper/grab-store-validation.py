import json
import time
from datetime import datetime
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import pandas as pd
from tqdm import tqdm
import gspread
from google.oauth2.service_account import Credentials
from gspread_formatting import *

# --- Import configurations from the separate config files ---
try:
    from credentials import ACCOUNT_CREDS
except ImportError:
    print("[FATAL] `credentials.py` not found. Please create it with your `ACCOUNT_CREDS` dictionary.")
    exit()

try:
    from settings import (
        GRAB_MERCHANT_CONFIG, TARGET_API_URL, COLUMN_MAPPING,
        GOOGLE_CREDS_FILE, GOOGLE_SHEET_NAME, INPUT_WORKSHEET_NAME, SINGLE_OUTLET_CHECK_URL, OUTPUT_WORKSHEET_NAME,
    )
except ImportError:
    print("[FATAL] `settings.py` not found. Please create it with your application settings.")
    exit()

# --- Logging Function ---


def log(level, message):
    """Prints a message to the console with a timestamp and log level."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level.upper()}] {message}")

# --- Browser Session Class for Robustness ---


class BrowserSession:
    """Manages the browser lifecycle, including login, logout, and navigation."""

    def __init__(self):
        log("info", "🚀 Initializing browser...")
        try:
            service = Service(ChromeDriverManager().install())
            options = webdriver.ChromeOptions()
            # options.add_argument("--headless")
            options.add_argument(
                '--disable-blink-features=AutomationControlled')

            selenium_wire_options = {'disable_encoding': True}

            self.driver = webdriver.Chrome(
                service=service,
                options=options,
                seleniumwire_options=selenium_wire_options
            )
            self.driver.set_page_load_timeout(60)
            self.wait = WebDriverWait(self.driver, 60)
            self.current_account = None
        except Exception as e:
            log("fatal", f"Failed to initialize browser session: {e}")
            self.driver = None

    def safe_get(self, url):
        """Navigates to a URL with a try-except block for timeouts."""
        try:
            self.driver.get(url)
            return True
        except TimeoutException:
            log("error", f"Page took too long to load and timed out: {url}")
            return False

    def handle_generic_popups(self):
        """Looks for common pop-ups (like cookie banners) and closes them."""
        try:
            cookie_button_xpath = "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]"
            short_wait = WebDriverWait(self.driver, 6)
            cookie_button = short_wait.until(
                EC.element_to_be_clickable((By.XPATH, cookie_button_xpath)))
            cookie_button.click()
            log("info", "   Closed a generic pop-up/cookie banner.")
        except (TimeoutException, NoSuchElementException):
            pass

    def handle_welcome_modal(self):
        """Looks for a specific 'Tutup' welcome modal and closes it."""
        try:
            short_wait = WebDriverWait(self.driver, 10)
            close_button_xpath = "//button[span[text()='Tutup'] or contains(@class, 'btn-skip')]"

            log("info", "   Checking for the welcome modal...")
            welcome_modal_button = short_wait.until(
                EC.element_to_be_clickable((By.XPATH, close_button_xpath))
            )
            welcome_modal_button.click()
            log("info", "   Closed the welcome modal.")
            time.sleep(1)
        except TimeoutException:
            log("info", "   Welcome modal not found, proceeding.")
            pass

    def login(self, account_name, account_creds):
        """Handles the full login flow for a given account and navigates to the starting page."""
        portal_config = GRAB_MERCHANT_CONFIG
        if self.current_account == account_name:
            log("info", f"✅ Already logged in with {account_name} account.")
            if not self.safe_get(portal_config['merchant_list_url']):
                log("error", "Failed to re-navigate to the menu page.")
                return False
            return True

        if self.current_account is not None:
            log("info",
                f"🔄 Switching accounts. Logging out from {self.current_account} first...")
            self.logout()

        log("info", f"🔑 Attempting to log in with {account_name} account...")
        if not self.safe_get(portal_config["login_url"]):
            return False

        try:
            self.handle_generic_popups()

            try:
                log("info", "   Checking for Login as another user button...")
                another_user_button_wait = WebDriverWait(self.driver, 2)
                another_user_button = another_user_button_wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//p[text()='Login as another user'] | //div[text()='Login as another user']")))
                another_user_button.click()
                log("info", "   Clicked Login as another user.")
            except (TimeoutException, NoSuchElementException):
                log("info", "   No Login as another user button found, proceeding.")

            log("info", "   ➡️ Entering username...")
            username_field = self.wait.until(EC.visibility_of_element_located(
                (By.ID, portal_config["username_field_id"])))
            username_field.clear()
            username_field.send_keys(account_creds["username"])
            log("info", "   ➡️ Clicking continue after username...")
            continue_user_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, portal_config["continue_after_username_xpath"])))
            continue_user_button.click()

            log("info", "   ➡️ Entering password...")
            password_field = self.wait.until(EC.visibility_of_element_located(
                (By.ID, portal_config["password_field_id"])))
            password_field.clear()
            password_field.send_keys(account_creds["password"])

            log("info", "   ➡️ Clicking continue after password...")
            final_login_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, portal_config["continue_after_password_xpath"])))
            final_login_button.click()

            self.wait.until(EC.url_contains(
                "https://merchant.grab.com/dashboard"))
            if "login" in self.driver.current_url.lower():
                log("error", "Login failed. Check credentials or solve CAPTCHA.")
                return False

            log("success", f"✅ Login successful for {account_name}.")
            self.current_account = account_name
            self.handle_welcome_modal()

            log("info",
                f"Navigating to menu page: {portal_config['merchant_list_url']}")
            if not self.safe_get(portal_config['merchant_list_url']):
                log("error", "Failed to navigate to the menu page after login.")
                return False

            return True
        except (TimeoutException, NoSuchElementException) as e:
            log("error",
                f"❌ Error during login for {account_name}: A step failed. Check selectors. Details: {e}")
            self.current_account = None
            return False

    def logout(self):
        """Handles the logout process by navigating to the logout URL."""
        if self.current_account is None:
            return

        portal_config = GRAB_MERCHANT_CONFIG
        log("info", f"🔒 Logging out from {self.current_account} account...")
        try:
            if self.safe_get(portal_config["logout_url"]):
                time.sleep(3)
            log("success", "✅ Logout successful.")
            self.current_account = None
        except Exception as e:
            log("error", f"❌ Could not log out cleanly. Details: {e}")
            self.current_account = None

    def quit(self):
        if self.driver:
            log("info", "🛑 Closing browser.")
            self.driver.quit()

# --- Google Sheets Functions ---


def gsheet_auth():
    log("info", "Authenticating with Google Sheets API...")
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDS_FILE, scopes=scopes)
        client = gspread.authorize(creds)
        log("success", "Google Sheets authentication successful.")
        return client
    except FileNotFoundError:
        log("error",
            f"Google credentials file not found: '{GOOGLE_CREDS_FILE}'.")
        return None
    except Exception as e:
        log("error", f"An error occurred during Google authentication: {e}")
        return None


def read_from_gsheet(client, sheet_name, worksheet_name):
    log("info", f"Reading data from worksheet: '{worksheet_name}'...")
    try:
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        all_values = worksheet.get_all_values()
        if len(all_values) < 2:
            log("error", "No data found in the worksheet (or header is missing).")
            return None
        header = all_values[0]
        data = all_values[1:]
        df = pd.DataFrame(data, columns=header)
        log("success",
            f"✅ Successfully loaded {len(df)} rows from {GOOGLE_SHEET_NAME}.")
        return df
    except Exception as e:
        log("error",
            f"An error occurred while reading from the Google Sheet: {e}")
        return None


def write_to_gsheet(client, df, sheet_name, account_name):
    worksheet_name = f"{account_name}"

    log("info",
        f"Writing report for '{account_name}' to worksheet: '{worksheet_name}'...")
    try:
        spreadsheet = client.open(sheet_name)
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            worksheet.clear()
            log("info", f"-> Cleared existing data in '{worksheet_name}'.")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name, rows="1", cols="1")
            log("info", f"-> Created new worksheet: '{worksheet_name}'.")

        df_to_write = df.fillna('').astype(str)
        worksheet.update(
            [
                df_to_write.columns.values.tolist()
            ] + df_to_write.values.tolist()
        )
        log("success", f"Successfully wrote {len(df)} rows to the sheet.")

        if len(df_to_write) > 0:
            log("info", "Applying conditional formatting...")
            green_format = CellFormat(backgroundColor=Color(0.85, 0.96, 0.85))
            yellow_format = CellFormat(backgroundColor=Color(1, 0.95, 0.8))
            red_format = CellFormat(backgroundColor=Color(0.96, 0.85, 0.85))
            grey_format = CellFormat(backgroundColor=Color(0.9, 0.9, 0.9))

            headers = df_to_write.columns.values.tolist()
            try:
                name_result_col_letter = gspread.utils.rowcol_to_a1(
                    1, headers.index('Name Result') + 1)[0]
                address_result_col_letter = gspread.utils.rowcol_to_a1(
                    1, headers.index('Address Result') + 1)[0]

                name_result_range = f'{name_result_col_letter}2:{name_result_col_letter}{len(df_to_write) + 1}'
                address_result_range = f'{address_result_col_letter}2:{address_result_col_letter}{len(df_to_write) + 1}'

                rules = get_conditional_format_rules(worksheet)
                rules.clear()

                ranges_to_format = [GridRange.from_a1_range(name_result_range, worksheet),
                                    GridRange.from_a1_range(address_result_range, worksheet)]

                rules.append(ConditionalFormatRule(
                    ranges=ranges_to_format,
                    booleanRule=BooleanRule(condition=BooleanCondition(
                        'TEXT_CONTAINS', ['True']), format=green_format)
                ))
                rules.append(ConditionalFormatRule(
                    ranges=ranges_to_format,
                    booleanRule=BooleanRule(condition=BooleanCondition(
                        'TEXT_CONTAINS', ['Warning']), format=yellow_format)
                ))
                rules.append(ConditionalFormatRule(
                    ranges=ranges_to_format,
                    booleanRule=BooleanRule(condition=BooleanCondition(
                        'TEXT_CONTAINS', ['False']), format=red_format)
                ))
                rules.append(ConditionalFormatRule(
                    ranges=ranges_to_format,
                    booleanRule=BooleanRule(condition=BooleanCondition(
                        'TEXT_CONTAINS', ['N/A']), format=grey_format)
                ))

                rules.save()
                log("success", "Conditional formatting applied.")
            except ValueError as ve:
                log("warn",
                    f"Could not apply conditional formatting. Column not found? Error: {ve}")

        return True
    except Exception as e:
        log("error",
            f"An error occurred while writing to the Google Sheet: {e}")
        return False

# --- Data Collection and Validation ---


def restructure_data(df):
    tasks = []
    log("info", "🛠️ Restructuring data...")

    all_required_cols = set()
    for mapping in COLUMN_MAPPING:
        all_required_cols.update([
            mapping["outlet_name"],
            mapping["ofd_name_col"],
            mapping["id_col"]
        ])

    if not all_required_cols.issubset(df.columns):
        missing_cols = all_required_cols - set(df.columns)
        log("error",
            f"The following required columns are missing from your sheet: {', '.join(missing_cols)}")
        return []

    for index, row in df.iterrows():
        for mapping in COLUMN_MAPPING:
            ofd_name = row.get(mapping["ofd_name_col"])

            if pd.notna(ofd_name) and str(ofd_name).strip() != "":
                store_id_raw = row.get(mapping["id_col"])

                tasks.append({
                    "outlet_name": str(row.get(mapping["outlet_name"], "")).strip(),
                    "ofd_name": str(ofd_name).strip(),
                    "store_id": str(store_id_raw).strip() if pd.notna(store_id_raw) else "",
                    "source_portal": mapping["source_portal"],
                })
    return tasks


def collect_all_merchants(driver):
    log("info", "Starting data collection with sequential API check...")
    del driver.requests

    try:
        log("info", "Attempting to capture the main multi-outlet API (timeout: 10s)...")
        request = driver.wait_for_request(TARGET_API_URL, timeout=10)

        log("info", "Main search API was called. Proceeding with full data collection.")
        data = json.loads(request.response.body.decode('utf-8'))
        merchants_batch = data.get("merchants", [])
        has_more_data = data.get("hasMore", False)

        if len(merchants_batch) == 1 and not has_more_data:
            log("warn", "Main API confirms only 1 outlet. Treating as single-outlet account.")
            return None

        all_merchants = merchants_batch
        if not has_more_data:
            log("info", "Main API indicates all data was collected in the first request.")
            return all_merchants

        try:
            scrollable_element = driver.find_element(
                By.CSS_SELECTOR, "div.dui-table-body")
        except NoSuchElementException:
            log("error", "Could not find scrollable element even though API indicated more data.")
            return all_merchants

        page_scroll_attempts = 0
        while has_more_data:
            previous_merchant_count = len(all_merchants)
            del driver.requests
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_element)
            try:
                scroll_request = driver.wait_for_request(
                    TARGET_API_URL, timeout=60)
                if scroll_request and scroll_request.response:
                    data = json.loads(
                        scroll_request.response.body.decode('utf-8'))
                    merchants_batch = data.get("merchants", [])
                    if merchants_batch:
                        all_merchants.extend(merchants_batch)
                    if len(all_merchants) == previous_merchant_count:
                        page_scroll_attempts += 1
                        if page_scroll_attempts > 2:
                            log("error", "No new merchants after multiple scroll attempts. Forcing stop.")
                            break
                    else:
                        page_scroll_attempts = 0
                    has_more_data = data.get("hasMore", False)
            except (json.JSONDecodeError, TimeoutException):
                log("warn", "Timed out or failed to decode response while scrolling. Assuming no more data.")
                break
        return all_merchants

    except TimeoutException:
        log("info", "Main API not found. Checking for the single-outlet portal API (timeout: 20s)...")

        # --- STEP 2: Try to capture the PORTAL (single-outlet) API ---
        try:
            request = driver.wait_for_request(
                SINGLE_OUTLET_CHECK_URL, timeout=20)
            log("info", "Portal API was called, indicating a single-outlet account.")
            return None
        except TimeoutException:
            log("error", "Did not capture any merchant data API call within the timeout period.")
            return []

    except json.JSONDecodeError as e:
        log("error", f"Failed to decode API response. Error: {e}")
        return []

    return []


def create_single_outlet_report(tasks_for_account):
    """Creates a DataFrame where all results are False for a single-outlet account."""
    log("info", "Generating a report for single-outlet account...")
    results = []
    for task in tasks_for_account:
        results.append({
            'Outlet Name': task['outlet_name'],
            'Outlet Name (OFD)': task['ofd_name'],
            'Store ID': task['store_id'],
            'Name Result': 'False',
            'Name Status (Blank)': '',
            'Actual Outlet Name': '',
            'Address Result': 'False',
            'Address Status (Blank)': '',
            'Actual Address': '',
            'Status': '',
            'Integration Status': ''
        })
    return pd.DataFrame(results)


def perform_validation(portal_data_df, tasks_to_validate):
    log("info",
        f"Performing validation logic for {len(tasks_to_validate)} tasks...")
    results = []
    if 'merchantID' in portal_data_df.columns:
        portal_data_df['merchantID'] = portal_data_df['merchantID'].astype(str)

    portal_dict = portal_data_df.set_index('merchantID').to_dict('index')

    for task in tqdm(tasks_to_validate, desc="Validating Merchants"):
        merchant_id = task['store_id']
        outlet_name_sheet = task['outlet_name']
        ofd_name_sheet = task['ofd_name']

        output_row = {
            'Outlet Name': outlet_name_sheet,
            'Outlet Name (OFD)': ofd_name_sheet,
            'Store ID': merchant_id,
            'Name Result': 'N/A',
            'Name Status (Blank)': '',
            'Actual Outlet Name': '',
            'Address Result': 'N/A',
            'Address Status (Blank)': '',
            'Actual Address': '',
            'Status': '',
            'Integration Status': ''
        }

        if not merchant_id:
            output_row['Status'] = 'Skipped - Missing Store ID'
            results.append(output_row)
            continue

        portal_record = portal_dict.get(merchant_id)

        if portal_record:
            name_portal = str(portal_record.get('merchantName', '')).strip()
            output_row['Actual Outlet Name'] = name_portal
            if not ofd_name_sheet:
                output_row['Name Result'] = 'False'
                output_row['Status'] = 'Skipped - Missing OFD Name'
            elif ofd_name_sheet.lower() == name_portal.lower():
                output_row['Name Result'] = 'True'
                output_row['Actual Outlet Name'] = ''
            else:
                output_row['Name Result'] = 'Warning'

            address_portal = str(portal_record.get('address', '')).strip()
            output_row['Actual Address'] = address_portal
            if not outlet_name_sheet:
                output_row['Address Result'] = 'False'
            elif outlet_name_sheet.lower() in address_portal.lower():
                output_row['Address Result'] = 'True'
                output_row['Actual Address'] = ''
            else:
                output_row['Address Result'] = 'Warning'

            if not output_row['Status']:
                output_row['Status'] = portal_record.get('status', 'Unknown')
            output_row['Integration Status'] = portal_record.get(
                'modelType', 'Unknown')

        else:
            output_row['Status'] = 'Not Found in Portal Scrape'
            output_row['Name Result'] = 'False'
            output_row['Address Result'] = 'False'

        results.append(output_row)

    log("success", "Validation complete for this batch.")
    return pd.DataFrame(results)


# --- Main Execution ---
if __name__ == "__main__":
    print("=" * 70)
    print("=== Grab Merchant Validator (Batch Mode with Separate Sheets) ===")
    print("=" * 70)

    gsheet_client = gsheet_auth()
    if not gsheet_client:
        exit()

    input_df = read_from_gsheet(
        gsheet_client, GOOGLE_SHEET_NAME, INPUT_WORKSHEET_NAME)
    if input_df is None:
        exit()

    all_tasks = restructure_data(input_df)
    if not all_tasks:
        log("error", "No tasks were created from the input data. Exiting.")
        exit()

    browser_session = BrowserSession()
    if not browser_session.driver:
        log("fatal", "Browser session failed to initialize. Exiting.")
        exit()

    while True:
        account_list = list(ACCOUNT_CREDS.keys())
        print("\n" + "=" * 70)
        log("info", "Please select an option:")

        # --- Modified Menu with "Run All" option ---
        print("   1. Run All Accounts")
        for i, name in enumerate(account_list):
            print(f"   {i+2}. {name}")
        print(f"   {len(account_list) + 2}. Exit")
        print("=" * 70)

        choice_input = input(f"Enter number (1-{len(account_list) + 2}): ")
        try:
            choice = int(choice_input)
        except ValueError:
            log("error", "Invalid input. Please enter a number.")
            continue

        accounts_to_process = []
        # --- Modified choice handling ---
        if choice == 1:
            log("info", "Option selected: Run All Accounts.")
            accounts_to_process = account_list
        elif 2 <= choice <= len(account_list) + 1:
            selected_account = account_list[choice - 2]
            log("info", f"Option selected: Run account '{selected_account}'.")
            accounts_to_process.append(selected_account)
        elif choice == len(account_list) + 2:
            log("info", "Exit choice selected.")
            break
        else:
            log("error", f"Invalid choice '{choice_input}'. Please try again.")
            continue

        # --- Consolidated processing loop ---
        for account_name in accounts_to_process:
            print("-" * 70)
            log("info",
                f"--- Starting processing for account: {account_name} ---")
            account_creds = ACCOUNT_CREDS[account_name]

            tasks_for_selected_account = [
                task for task in all_tasks if task['source_portal'] == account_name
            ]
            if not tasks_for_selected_account:
                log("warn",
                    f"No tasks found for account '{account_name}' in the input sheet. Skipping.")
                continue

            log("info",
                f"Found {len(tasks_for_selected_account)} tasks for this account.")

            try:
                if browser_session.login(account_name, account_creds):
                    merchants_data = collect_all_merchants(
                        browser_session.driver)

                    if merchants_data is None:
                        log("info",
                            f"'{account_name}' is a single-outlet account. Writing 'False' report.")
                        report_df = create_single_outlet_report(
                            tasks_for_selected_account)
                        write_to_gsheet(gsheet_client, report_df,
                                        GOOGLE_SHEET_NAME, account_name)
                        log("success",
                            f"✅ Report for {account_name} saved successfully!")

                    elif merchants_data:
                        log("success",
                            f"Data collection complete! Found {len(merchants_data)} total merchants in portal.")
                        portal_df = pd.DataFrame(merchants_data).drop_duplicates(
                            subset=['merchantID'])
                        log("info",
                            f"-> {len(portal_df)} unique merchants to be used for validation.")

                        report_df = perform_validation(
                            portal_df, tasks_for_selected_account)

                        if not report_df.empty:
                            write_to_gsheet(gsheet_client, report_df,
                                            GOOGLE_SHEET_NAME, account_name)
                            log("success",
                                f"✅ Report for {account_name} saved successfully!")
                        else:
                            log("warn", "Validation produced no results. Nothing to write.")

                    else:
                        log("error",
                            f"No merchant data collected from portal for account '{account_name}'.")
                else:
                    log("warn",
                        f"Login failed for account '{account_name}'. Skipping.")
            except Exception as e:
                log("fatal",
                    f"An unexpected error occurred during processing for {account_name}: {e}")

        if accounts_to_process:
            log("info", "Batch finished. Returning to main menu.")

    browser_session.quit()
    log("info", "Process finished.")
