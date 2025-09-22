import json
import time
import random
import os
import shutil
import gzip
import re
from datetime import datetime
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_formatting import *

# --- Import configurations ---
try:
    from credentials import ACCOUNT_CREDS
except ImportError:
    print("[FATAL] `credentials.py` not found. Please create it.")
    exit()

try:
    from settings import (
        GOOGLE_CREDS_FILE, GOOGLE_SHEET_NAME, INPUT_WORKSHEET_NAME, COLUMN_MAPPING
    )
except ImportError:
    print("[FATAL] `settings.py` not found. Please create it.")
    exit()


# --- Logging Function ---
def log(level, message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level.upper()}] {message}")

# --- Browser Session Class ---


class BrowserSession:
    def __init__(self):
        log("info", "🚀 Initializing stealth browser session...")
        try:
            options = webdriver.ChromeOptions()
            options.add_argument(
                "--disable-blink-features=AutomationControlled")
            options.add_experimental_option(
                "excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--window-size=1920,1080")
            options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
            script_dir = os.path.dirname(__file__)
            profile_path = os.path.join(
                script_dir, "selenium_profiles", "shopee_profile")
            options.add_argument(f"--user-data-dir={profile_path}")
            self.driver = webdriver.Chrome(service=Service(
                ChromeDriverManager().install()), options=options)
            self.wait = WebDriverWait(self.driver, 30)
            self.current_account = None
        except Exception as e:
            log("fatal", f"Failed to initialize browser session: {e}")
            self.driver = None

    def login(self, account_name, creds):
        if self.current_account == account_name:
            return True
        elif self.current_account is not None:
            log("info",
                f"🔄 Switching accounts from {self.current_account} to {account_name}.")
        log("info", f"🔑 Attempting to log in with {account_name} account...")
        self.driver.get(
            'https://partner.business.accounts.shopee.co.id/authenticate/login/')
        try:
            time.sleep(random.uniform(2.0, 4.0))
            if "/select" not in self.driver.current_url and "/food/dashboard" not in self.driver.current_url:
                log("info", "  ➡️ Entering credentials...")
                username_field = self.wait.until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'input[placeholder="No. handphone / Username / Email"]')))
                username_field.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                username_field.send_keys(creds["username"])
                password_field = self.wait.until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'input[placeholder="Password"]')))
                password_field.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                password_field.send_keys(creds["password"])
                self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(., 'Masuk')]"))).click()
                try:
                    WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(., 'Lanjutkan')]"))).click()
                    log("info", "  ➡️ Clicked optional 'Continue' button.")
                except TimeoutException:
                    pass

            time.sleep(random.uniform(2.0, 3.0))
            if "/food/dashboard" not in self.driver.current_url:
                log("info", "  ➡️ Selecting merchant profile...")
                profile_selector = (By.CSS_SELECTOR, 'div.listItem')
                merchant_profile = self.wait.until(
                    EC.visibility_of_element_located(profile_selector))
                ActionChains(self.driver).move_to_element(merchant_profile).pause(
                    random.uniform(0.5, 1.0)).click().perform()

            self.wait.until(EC.url_contains('/food/dashboard'))
            log("success", f"✅ Login successful for {account_name}.")
            self.current_account = account_name
            return True
        except (TimeoutException, NoSuchElementException) as e:
            log("error",
                f"❌ Error during login for {account_name}. Details: {e}")
            return False

    def quit(self):
        if self.driver:
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
    except Exception as e:
        log("error", f"An error occurred during Google authentication: {e}")
        return None


def read_from_gsheet(client, sheet_name, worksheet_name):
    log("info", f"Reading data from worksheet: '{worksheet_name}'...")
    try:
        worksheet = client.open(sheet_name).worksheet(worksheet_name)
        data = worksheet.get_all_values()
        if len(data) < 2:
            return None
        df = pd.DataFrame(data[1:], columns=data[0])
        log("success", f"✅ Successfully loaded {len(df)} rows.")
        return df
    except Exception as e:
        log("error",
            f"An error occurred while reading from the Google Sheet: {e}")
        return None


def write_to_gsheet(client, df, sheet_name, worksheet_name):
    log("info", f"Writing report to worksheet: '{worksheet_name}'...")
    try:
        spreadsheet = client.open(sheet_name)
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            worksheet.clear()
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name, rows="1", cols="1")

        df_to_write = df.fillna('').astype(str)
        worksheet.update(
            [
                df_to_write.columns.values.tolist()
            ] + df_to_write.values.tolist()
        )
        log("success", f"Successfully wrote {len(df)} rows to the sheet.")
    except Exception as e:
        log("error",
            f"An error occurred while writing to the Google Sheet: {e}")

# --- Data Handling Functions ---


def restructure_data(df):
    tasks = []
    log("info", "🛠️ Restructuring data from spreadsheet...")
    for mapping in COLUMN_MAPPING:
        for index, row in df.iterrows():
            ofd_name = row.get(mapping["ofd_name_col"])
            store_id = row.get(mapping["id_col"])
            if pd.notna(store_id) and str(store_id).strip() != "":
                tasks.append({
                    "outlet_name": str(row.get(mapping["outlet_name"], "")).strip(),
                    "ofd_name": str(ofd_name).strip() if pd.notna(ofd_name) else "",
                    "store_id": str(store_id).strip(),
                    "source_portal": mapping["source_portal"],
                })
    return tasks


def collect_shopee_stores(driver, wait):
    log("info", "  Navigating to Shopee POS page...")
    try:
        driver.get('https://partner.shopee.co.id/shopee-pos')
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                (By.XPATH, "//button[span[text()='OK']]"))).click()
            time.sleep(random.uniform(1.5, 2.5))
        except TimeoutException:
            pass

        del driver.requests
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'div.shop-select-preview'))).click()
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(@class, 'select-dropdown-item')]"))).click()

        api_pattern = re.compile(r'foody\.shopee\.co\.id/api/seller/stores?$')
        request = driver.wait_for_request(api_pattern, timeout=30)

        if not request.response:
            return None
        body = gzip.decompress(request.response.body).decode('utf-8') if request.response.headers.get(
            'Content-Encoding') == 'gzip' else request.response.body.decode('utf-8')
        data = json.loads(body).get('data', {})

        stores = data.get('stores') or (
            [data.get('store')] if data.get('store') else [])
        log("success",
            f"  Successfully captured data for {len(stores)} stores.")
        return stores
    except Exception as e:
        log("error", f"  An error occurred while collecting store data: {e}")
        return None


def perform_validation(portal_data, tasks_to_validate):
    log("info", f"Performing validation for {len(tasks_to_validate)} tasks...")
    results = []
    portal_dict = {str(store['id']): store for store in portal_data}

    for task in tasks_to_validate:
        store_id = task['store_id']
        portal_record = portal_dict.get(store_id)

        name_result = "Not Found"
        actual_name = ""

        if portal_record:
            actual_name = portal_record.get('name', '').strip()
            if task['ofd_name'].lower() == actual_name.lower():
                name_result = "Match"
            else:
                name_result = "Mismatch"

        results.append({
            'Source Portal': task['source_portal'],
            'Outlet Name': task['outlet_name'],
            'Store ID': store_id,
            'Outlet Name (OFD)': task['ofd_name'],
            'Actual Name': actual_name,
            'Name Result': name_result,
            'Name Status(Blank)': "",
            'Actual Outlet Name': actual_name,
            'Address Result': "",
            'Address Status(Blank)': "",
            'Actual Address': portal_record.get('address', '') if portal_record else ""
        })

    log("success", "Validation complete.")
    return pd.DataFrame(results)


# --- Main Execution ---
if __name__ == "__main__":
    gsheet_client = gsheet_auth()
    if not gsheet_client:
        exit()
    input_df = read_from_gsheet(
        gsheet_client, GOOGLE_SHEET_NAME, INPUT_WORKSHEET_NAME)
    if input_df is None:
        exit()
    all_tasks = restructure_data(input_df)
    if not all_tasks:
        exit()

    browser_session = None
    while True:
        account_list = list(ACCOUNT_CREDS.keys())
        print("\n" + "="*70)
        log("info", "Please select an option:")
        print("  1. Run All Accounts")
        for i, name in enumerate(account_list):
            print(f"  {i+2}. {name}")
        print(f"  {len(account_list) + 2}. Manual Login Setup")
        print(f"  {len(account_list) + 3}. Reset Profile (Clear Session)")
        print(f"  {len(account_list) + 4}. Exit")
        print("="*70)

        try:
            choice = int(input(f"Enter number (1-{len(account_list) + 4}): "))
        except ValueError:
            log("error", "Invalid input.")
            continue

        if choice == len(account_list) + 4:
            break
        elif choice == len(account_list) + 2:
            if browser_session is None:
                browser_session = BrowserSession()
            log("info", "Browser open for 5 mins for manual login. Close manually when done.")
            time.sleep(300)
            continue
        elif choice == len(account_list) + 3:
            profile_path = os.path.join(os.path.dirname(
                __file__), "selenium_profiles", "shopee_profile")
            if os.path.exists(profile_path):
                if input(f"  [WARNING] Delete profile folder? [y/N]: ").lower() == 'y':
                    try:
                        shutil.rmtree(profile_path)
                        log("success", "✅ Profile folder deleted.")
                    except Exception as e:
                        log("error", f"Could not delete profile folder: {e}")
            else:
                log("info", "Profile folder does not exist.")
            continue

        accounts_to_process = account_list if choice == 1 else [
            account_list[choice - 2]]

        if browser_session is None:
            browser_session = BrowserSession()
        if not browser_session.driver:
            break

        for account_name in accounts_to_process:
            print("-" * 70)
            log("info",
                f"--- Starting processing for account: {account_name} ---")

            tasks_for_account = [
                t for t in all_tasks if t['source_portal'] == account_name]
            if not tasks_for_account:
                log("warn",
                    f"No tasks found for account '{account_name}'. Skipping.")
                continue

            if browser_session.login(account_name, ACCOUNT_CREDS[account_name]):
                store_data = collect_shopee_stores(
                    browser_session.driver, browser_session.wait)
                if store_data:
                    report_df = perform_validation(
                        store_data, tasks_for_account)
                    write_to_gsheet(gsheet_client, report_df,
                                    GOOGLE_SHEET_NAME, f"Report_{account_name}")
                else:
                    log("error",
                        f"No store data collected for {account_name}. Cannot generate report.")
            else:
                log("warn",
                    f"Login failed for account '{account_name}'. Skipping.")

    if browser_session:
        browser_session.quit()
    log("info", "Process finished.")
