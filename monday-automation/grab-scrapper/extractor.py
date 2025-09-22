import json
import time
from datetime import datetime
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- Import configurations from the separate config files ---
try:
    from credentials import ACCOUNT_CREDS
except ImportError:
    print("[FATAL] `credentials.py` not found. Please create it with your `ACCOUNT_CREDS` dictionary.")
    exit()

try:
    from settings import (
        GRAB_MERCHANT_CONFIG, TARGET_API_URL,
        GOOGLE_CREDS_FILE, GOOGLE_SHEET_NAME, SINGLE_OUTLET_CHECK_URL
    )
except ImportError:
    print("[FATAL] `settings.py` not found. Please create it with the script's settings.")
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
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 20)
            self.current_account = None
        except Exception as e:
            log("fatal", f"Failed to initialize browser session: {e}")
            self.driver = None

    def safe_get(self, url):
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
            log("info", "   🤖 Closed a generic pop-up/cookie banner.")
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
                log("info", "   Checking for 'Login as another user' button...")
                another_user_button_wait = WebDriverWait(self.driver, 2)
                another_user_button = another_user_button_wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//p[text()='Login as another user'] | //div[text()='Login as another user']")))
                another_user_button.click()
                log("info", "   Clicked 'Login as another user'.")
            except (TimeoutException, NoSuchElementException):
                log("info", "   No 'Login as another user' button found, proceeding.")

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
        if self.current_account is None:
            return
        log("info", f"🔒 Logging out from {self.current_account} account...")
        self.safe_get(GRAB_MERCHANT_CONFIG["logout_url"])
        time.sleep(3)
        log("success", "✅ Logout successful.")
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
        return gspread.authorize(creds)
    except Exception as e:
        log("error", f"Google authentication failed: {e}")
        return None


def write_to_gsheet(client, df, sheet_name, worksheet_name):
    """Writes a DataFrame to a specific worksheet."""
    log("info",
        f"Writing data to spreadsheet '{sheet_name}' in worksheet: '{worksheet_name}'...")
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
            ] + df_to_write.values.tolist())
        log("success",
            f"Successfully wrote {len(df)} rows to '{worksheet_name}'.")
    except Exception as e:
        log("error",
            f"An error occurred while writing to the Google Sheet: {e}")

# --- Data Collection ---


def collect_all_merchants(driver):
    log("info", "Starting data collection with sequential API check...")
    del driver.requests

    try:
        # --- STEP 1: First, try to capture the MAIN (multi-outlet) API ---
        log("info", "Attempting to capture the main multi-outlet API (timeout: 20s)...")
        request = driver.wait_for_request(TARGET_API_URL, timeout=20)

        log("info", "Main search API was called. Proceeding with full data collection.")
        data = json.loads(request.response.body.decode('utf-8'))
        merchants_batch = data.get("merchants", [])
        has_more_data = data.get("hasMore", False)

        if len(merchants_batch) == 1 and not has_more_data:
            log("info", "Main API returned only 1 outlet with no more data.")
            return merchants_batch

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
        try:
            request = driver.wait_for_request(
                SINGLE_OUTLET_CHECK_URL, timeout=20)
            log("info", "Portal API was called. Extracting single outlet data.")
            if request and request.response:
                data = json.loads(request.response.body.decode('utf-8'))
                single_merchant_list = data.get("merchants", [])
                return single_merchant_list
            else:
                return []
        except TimeoutException:
            log("error", "Did not capture any merchant data API call within the timeout period.")
            return []

    except json.JSONDecodeError as e:
        log("error", f"Failed to decode API response. Error: {e}")
        return []

    return []


# --- Main Execution ---
if __name__ == "__main__":
    print("=" * 50)
    print("=== Grab Merchant Data Extractor ===")
    print("=" * 50)

    gsheet_client = gsheet_auth()
    if not gsheet_client:
        exit()

    browser = BrowserSession()
    if not browser.driver:
        exit()

    while True:
        account_list = list(ACCOUNT_CREDS.keys())
        print("\n" + "=" * 70)
        log("info", "Please select an option:")

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
        run_all_mode = False

        if choice == 1:
            log("info", "Option selected: Run All Accounts.")
            accounts_to_process = account_list
            run_all_mode = True
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

        # List to hold DataFrames for the "Run All" mode
        all_accounts_data = []

        for account_name in accounts_to_process:
            print("-" * 70)
            log("info",
                f"--- Starting extraction for account: {account_name} ---")
            account_creds = ACCOUNT_CREDS[account_name]

            try:
                if browser.login(account_name, account_creds):
                    merchants = collect_all_merchants(browser.driver)

                    if merchants:
                        log("success",
                            f"Data collection complete! Found {len(merchants)} merchants for '{account_name}'.")

                        portal_df = pd.DataFrame(merchants).drop_duplicates(
                            subset=['merchantID'])

                        output_df = portal_df[
                            [
                                'merchantID',
                                'merchantName',
                                'status',
                                'modelType'
                            ]
                        ].copy()

                        # Add the new 'Portal' column at the beginning
                        output_df.insert(0, 'Portal', account_name)

                        output_df.rename(columns={
                            'merchantID': 'Store ID',
                            'merchantName': 'Actual Outlet Name',
                            'status': 'Outlet Status',
                            'modelType': 'Integration Status'
                        }, inplace=True)

                        if run_all_mode:
                            all_accounts_data.append(output_df)
                        else:
                            # If it's a single run, write it immediately
                            worksheet_name = f"E-{account_name}"
                            write_to_gsheet(gsheet_client, output_df,
                                            GOOGLE_SHEET_NAME, worksheet_name)
                    else:
                        log("error",
                            f"No merchant data was collected for '{account_name}'.")
            except Exception as e:
                log("fatal",
                    f"An unexpected error occurred for '{account_name}': {e}")

        # After the loop, if in "Run All" mode, combine and write the data
        if run_all_mode and all_accounts_data:
            log("info", "Combining data from all accounts...")
            final_df = pd.concat(all_accounts_data, ignore_index=True)
            log("success",
                f"Combined a total of {len(final_df)} records from {len(all_accounts_data)} accounts.")

            worksheet_name = "Grab All Portal Extract"
            write_to_gsheet(gsheet_client, final_df,
                            GOOGLE_SHEET_NAME, worksheet_name)
        elif run_all_mode:
            log("warn", "Run All mode finished, but no data was collected from any account.")

        if accounts_to_process:
            log("info", "Batch finished. Returning to main menu.")

    browser.quit()
    log("info", "Process finished.")
