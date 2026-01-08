import json
import time
import random
import os
import shutil
import gzip
import re
import requests
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
from dotenv import load_dotenv
from datetime import timezone, timedelta

try:
    from modules.shopee.browser_session import BrowserSession
    from common.logger import get_logger
    from common.monday_api import execute_monday_query
    from common.shopee_utils import get_current_merchant_name, switch_merchant
    from common.http_utils import parse_response_json, decompress_response_body
    from config.credentials_shopee import ACCOUNT_CREDS
    from config.settings_shopee import MERCHANT_PROCESSING_LIST
except ImportError as e:
    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [FATAL] An import failed: {e}. Ensure `credentials.py` and `settings.py` are created and configured."
    )
    exit()

# Get logger instance
log = get_logger("shopee_customer")


# --- Load Environment Variables for Notifications ---
load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# --- Selenium and Data Collection Functions ---


def collect_transaction_data(browser_session):
    """
    Navigate to transactions, APPLY DATE FILTER, and scrape transaction details.
    """
    driver = browser_session.driver
    wait = browser_session.wait
    all_transactions_list = []
    all_order_details = []

    # Regex for the transaction list API
    api_list_pattern = re.compile(
        r"api\.partner\.shopee\.co\.id/nb/mss/web-api/PartnerTransactionServer/GetTransactionList"
    )
    api_detail_pattern = re.compile(
        r"foody\.shopee\.co\.id/api/seller/mis/orders/(\d+)"
    )

    try:
        # NEW: Ensure we are logged in before proceeding
        if not browser_session.ensure_logged_in():
            log.critical(
                "  Failed to ensure login. Aborting collection for this merchant."
            )
            return None

        log.info("    Navigating to Transactions page...")
        driver.get("https://partner.shopee.co.id/food/transactions")

        # ============================================================
        #  START: INTEGRATED DATE PICKER SCRIPT
        # ============================================================
        try:
            log.info("    [DatePicker] Opening date picker...")

            # 1. Open Date Picker (Targeting the input wrapper)
            date_picker_input = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".ant-picker-input input#timePeriod")
                )
            )
            date_picker_input.click()
            time.sleep(0.5)  # Short wait for dropdown animation

            # 2. Loop: Click "Prev" FIRST, then check (as requested)
            log.info("    [DatePicker] Searching for start date boundary...")

            while True:
                # --- STEP A: Click Previous First ---
                try:
                    prev_btn = driver.find_element(
                        By.CLASS_NAME, "ant-picker-header-prev-btn"
                    )
                    prev_btn.click()
                    log.info(
                        "    [DatePicker] Clicked 'Previous' month button."
                    )  # LOGGING ADDED
                    time.sleep(0.5)  # Wait for calendar animation
                except Exception as e:
                    log.warning(
                        f"    [DatePicker] Could not click previous button (limit reached?): {e}"
                    )
                    break

                # --- STEP B: Check for disabled cells ---
                # We look for the specific class combination indicating a disabled cell in the current view
                disabled_cells = driver.find_elements(
                    By.CSS_SELECTOR,
                    ".ant-picker-cell.ant-picker-cell-disabled.ant-picker-cell-in-view",
                )

                if len(disabled_cells) > 0:
                    log.info(
                        "    [DatePicker] Found disabled cells. Stopping navigation."
                    )
                    break

            # 3. Select the first valid date (Linear Search)
            # This handles the logic of "end of row" vs "start of next row" automatically
            all_cells = driver.find_elements(
                By.CSS_SELECTOR, "td.ant-picker-cell-in-view"
            )
            target_cell = None

            for cell in all_cells:
                # If the cell DOES NOT have 'ant-picker-cell-disabled', it is the first valid date
                if "ant-picker-cell-disabled" not in cell.get_attribute("class"):
                    target_cell = cell
                    break

            if target_cell:
                log.info(f"    [DatePicker] Selecting start date: {target_cell.text}")
                target_cell.click()
            else:
                log.warning(
                    "    [DatePicker] Could not find a valid date in the current view."
                )

            # 4. Click "Terapkan" (Apply)
            # Locate button with class 'ant-btn-primary' that contains text 'Terapkan'
            apply_btn = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//button[contains(@class, 'ant-btn-primary')]//span[contains(text(), 'Terapkan')]/..",
                    )
                )
            )

            # IMPORTANT: Clear previous requests (like the initial page load)
            # so we capture the NEW request generated by this filter.
            del driver.requests

            apply_btn.click()
            log.info(
                "    [DatePicker] Clicked 'Terapkan' and cleared previous API logs."
            )

        except Exception as e:
            # We log the error but continue, in case the date picker fails but default data is available
            log.error(f"    [DatePicker] Interaction failed: {e}")

        # ============================================================
        #  END: INTEGRATED DATE PICKER SCRIPT
        # ============================================================

        log.info("    Waiting for transaction list API call (Filtered)...")
        # Increase timeout slightly as filtering might take a moment
        initial_request = driver.wait_for_request(api_list_pattern, timeout=45)

        # --- Initial response processing (Page 1) ---
        if initial_request.response:
            response_json = parse_response_json(initial_request.response)

            if response_json and response_json.get("errorCode") != 0:
                log.error(
                    f"    Initial API call failed: {response_json.get('errorMsg')}. Cooldown and retry."
                )
                time.sleep(300)
                return collect_transaction_data(driver, wait)  # Retry

            data = response_json.get("data", {})
            initial_txs = data.get("list", [])
            all_transactions_list.extend(initial_txs)
            log.info(
                f"    Page 1 (initial load): Found {len(initial_txs)} transactions."
            )

        # --- Attempt to set page size to 50 ---
        try:
            log.info("    Attempting to set page size to 50...")
            fifty_per_page_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//button[contains(@class, 'page-size-item') and .//span[text()='50']]",
                    )
                )
            )
            del driver.requests
            fifty_per_page_button.click()
            log.info("    Waiting for API call after resizing page...")
            resize_request = driver.wait_for_request(api_list_pattern, timeout=30)

            if resize_request.response:
                response_text = decompress_response_body(resize_request.response)
                response_json = json.loads(response_text)
                if response_json.get("errorCode") == 0:
                    data = response_json.get("data", {})
                    all_transactions_list = data.get("list", [])
                    log.info(
                        f"    Page size set to 50. Page 1 now has {len(all_transactions_list)} transactions."
                    )
                else:
                    log.warning(
                        f"    API call after resize failed: {response_json.get('errorMsg')}"
                    )
        except TimeoutException:
            log.warning("    Could not set page size to 50. Proceeding with default.")

        # --- Pagination Loop ---
        page_count = 1
        while True:
            page_count += 1
            log.info(f"--- Checking for Page {page_count} ---")

            try:
                next_page_li = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//li[@title='Next Page']")
                    )
                )
                if next_page_li.get_attribute("aria-disabled") == "true":
                    log.info("    'Next Page' button is disabled. All pages collected.")
                    break  # End of pages

                del driver.requests
                next_page_li.click()

                log.info(f"    Waiting for API call for page {page_count}...")
                page_request = driver.wait_for_request(api_list_pattern, timeout=30)

                if not page_request.response:
                    raise TimeoutException("No response.")

                response_text = decompress_response_body(page_request.response)
                response_json = json.loads(response_text)

                if response_json.get("errorCode") == 0:
                    data = response_json.get("data", {})
                    new_txs = data.get("list", [])
                    if new_txs:
                        log.info(
                            f"    Page {page_count}: Found {len(new_txs)} new transactions."
                        )
                        all_transactions_list.extend(new_txs)
                    else:
                        log.warning(
                            "    New page returned 0 transactions. Stopping pagination."
                        )
                        break
                    time.sleep(random.uniform(3.0, 6.0))
                else:
                    # --- Error Recovery ---
                    log.error(
                        f"    Server error on page {page_count}: {response_json.get('errorMsg')}. Cooldown and recovery."
                    )
                    time.sleep(300)
                    log.error(f"    Recovery not implemented. Stopping pagination.")
                    break

            except (TimeoutException, NoSuchElementException):
                log.info(
                    "    Could not find 'next page' or timed out. Assuming end of pages."
                )
                break

        log.info(
            f"✅ Total transaction list collection complete. Found {len(all_transactions_list)} items."
        )

        if not all_transactions_list:
            log.warning("    No transactions found to process for details.")
            return []

        unique_transactions = (
            pd.DataFrame(all_transactions_list)
            .drop_duplicates(subset=["transactionId"])
            .to_dict("records")
        )
        total_to_process = len(unique_transactions)

        # --- Phase 2: Go back to page 1 and start UI processing ---
        log.info("    Navigating back to page 1 to begin detail scraping...")
        try:
            wait.until(
                EC.element_to_be_clickable((By.XPATH, "//li[@title='1']"))
            ).click()
            time.sleep(3)  # Wait for page to settle
        except Exception as e:
            log.error(f"    Could not navigate back to page 1. Aborting. Error: {e}")
            return None

        log.info(
            f"    Starting UI interaction for {total_to_process} unique transactions..."
        )

        items_per_page = 50
        for i, tx in enumerate(unique_transactions):
            # --- Page Navigation Logic ---
            if i > 0 and i % items_per_page == 0:
                log.info(
                    f"--- Processed {items_per_page} items, moving to next page... ---"
                )
                try:
                    next_page_button = wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//li[@title='Next Page']")
                        )
                    )
                    if next_page_button.get_attribute("aria-disabled") == "true":
                        log.warning(
                            "    Next page button is disabled, but there are more items to process. This may indicate an issue."
                        )
                        break
                    next_page_button.click()
                    time.sleep(3)  # Wait for next page to load
                except Exception as e:
                    log.error(
                        f"    Failed to navigate to the next page. Aborting. Error: {e}"
                    )
                    break

            tx_id = tx.get("transactionId")
            log.info(f"    Processing TxID {tx_id} ({i+1}/{total_to_process})...")

            try:
                # 1. Find the clickable div within the row
                tx_element_xpath = f"//tr[starts-with(@data-row-key, '{tx_id}')]//div[contains(@class, 'sc-cWSHoV hMWKbD')]"
                tx_element = wait.until(
                    EC.presence_of_element_located((By.XPATH, tx_element_xpath))
                )

                # 2. Scroll and click with JS
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", tx_element
                )
                time.sleep(0.5)
                del driver.requests
                driver.execute_script("arguments[0].click();", tx_element)

                # 3. Wait for detail API and extract data
                detail_request = driver.wait_for_request(api_detail_pattern, timeout=20)
                customer_name, customer_phone, place_time_gmt7 = None, None, None

                if detail_request.response:
                    detail_text = decompress_response_body(detail_request.response)
                    detail_json = json.loads(detail_text)
                    order_data = detail_json.get("data", {}).get("order", {})

                    # Extract customer details
                    delivery_address = order_data.get("delivery_address", {})
                    cust_address = delivery_address.get("address")
                    customer_name = delivery_address.get("name")
                    customer_phone = delivery_address.get("phone")

                    # --- NEW: Extract and convert place_time ---
                    place_time_ms_str = order_data.get("place_time")
                    if place_time_ms_str:
                        try:
                            place_time_s = int(place_time_ms_str) / 1000
                            gmt7_tz = timezone(timedelta(hours=7))
                            dt_object = datetime.fromtimestamp(place_time_s, tz=gmt7_tz)
                            place_time_gmt7 = dt_object.strftime("%Y-%m-%d %H:%M:%S")
                        except (ValueError, TypeError):
                            log.warning(
                                f"      Could not parse place_time: {place_time_ms_str}"
                            )

                    log.info(
                        f"      Found details: Name={customer_name}, Phone={customer_phone}"
                    )

                # 4. Close the modal
                try:
                    modal_wrapper_xpath = (
                        "//div[contains(@class, 'shopee-food-modal-wrap')]"
                    )
                    close_button_xpath = "//button[@aria-label='Close' and contains(@class, 'shopee-food-modal-close')]"
                    close_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, close_button_xpath))
                    )
                    close_button.click()
                    wait.until(
                        EC.invisibility_of_element_located(
                            (By.XPATH, modal_wrapper_xpath)
                        )
                    )
                    log.info("      Modal closed.")
                except Exception as e:
                    log.warning(
                        f"      Could not close modal. Refreshing page to recover. Error: {e}"
                    )
                    driver.refresh()
                    time.sleep(5)

            except (TimeoutException, NoSuchElementException) as e:
                log.error(
                    f"    Could not find or process TxID {tx_id} on the page. Skipping. Error: {e}"
                )
                continue
            except Exception as e:
                log.error(
                    f"    An unexpected error occurred processing {tx_id}. Refreshing and skipping. Error: {e}"
                )
                driver.refresh()
                time.sleep(5)
                continue

            # 5. Add data to final list
            all_order_details.append(
                {
                    "transactionId": tx_id,
                    "amount": tx.get("amount"),
                    "merchantName": tx.get("merchantName"),
                    "customer_name": customer_name,
                    "customer_phone": customer_phone,
                    "place_time_gmt7": place_time_gmt7,
                }
            )

        return all_order_details

    except Exception as e:
        log.error(f"    An unrecoverable error occurred during data collection: {e}")
        return None


def upload_transactions_to_monday(board_id, group_id, transaction_data, portal_name):
    """(This function is no longer called but is kept for future use)"""
    log.info(
        f"Uploading {len(transaction_data)} transactions to Monday.com board '{board_id}'..."
    )

    log.info(
        f"    Fetching ALL existing items from group '{group_id}' (using pagination)..."
    )

    existing_items_map = {}
    # ... (rest of the function is unchanged) ...
    log.info(f"✅ Monday.com board update complete for this merchant.")


def run_customer_details_sync(browser_session, merchant_task):
    """
    The core logic for syncing customer details for a single merchant.
    This function is called by the main_runner.
    """
    OUTPUT_DIR = "scraped_data"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    portal_data = collect_transaction_data(browser_session)

    if portal_data:
        log.info(f"    Successfully collected {len(portal_data)} transaction details.")

        # Create a clean filename
        merchant_name = merchant_task.get("output_name", "unknown_merchant")
        safe_filename = re.sub(r'[\\/*?:"<>|]', "", merchant_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_filename}_{timestamp}.xlsx"
        filepath = os.path.join(OUTPUT_DIR, filename)

        try:
            log.info(f"    Writing data to Excel file: {filepath}")
            df = pd.DataFrame(portal_data)
            df.to_excel(filepath, index=False)
            log.info(f"✅ Data saved successfully to {filepath}")
        except Exception as e:
            log.error(f"    Failed to write Excel file: {e}")
    else:
        log.error(f"No data collected for {merchant_task['validate_name']}.")
