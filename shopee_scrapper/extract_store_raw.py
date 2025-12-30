import json
import time
import random
import os
import gzip
import re
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    # Assuming this script is run from the `shopee_scraper` directory
    from browser_session import BrowserSession, log
    from common.shopee_utils import get_current_merchant_name, switch_merchant
    from common.http_utils import parse_response_json
    from shopee_scrapper.pagination_utils import jump_to_page
    from shopee_scrapper.config.credentials import ACCOUNT_CREDS
    from shopee_scrapper.config.settings import MERCHANT_PROCESSING_LIST
except ImportError:
    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [FATAL] Ensure `credentials.py` and `settings.py` are created and configured."
    )
    exit()


def collect_shopee_raw_data(browser_session, merchant_name):
    """
    Collects store data and saves it to a raw JSON file in the 'raw_data' directory.
    """
    api_pattern = re.compile(r"foody\.shopee\.co\.id/api/seller/stores/search")
    driver = browser_session.driver
    wait = browser_session.wait

    # --- Stateful Logic: Define temp file and load previous state if it exists ---
    safe_merchant_name = re.sub(r'[\\/*?:"<>|]', "", merchant_name).replace(" ", "_")
    temp_file_path = f"temp_store_data_{safe_merchant_name}.json"
    all_stores = []
    start_page = 1

    if os.path.exists(temp_file_path):
        log.info(f"  Found temporary data file '{temp_file_path}'. Resuming session.")
        with open(temp_file_path, "r") as f:
            saved_state = json.load(f)
            all_stores = saved_state.get("stores", [])
            last_page = saved_state.get("last_page", 0)
            start_page = last_page + 1
            log.info(
                f"  Resuming from page {start_page}. Already have {len(all_stores)} stores.",
            )

    try:
        # --- Initial Page Load & Setup ---
        if not browser_session.ensure_logged_in():
            log.critical(
                "  Failed to ensure login. Aborting collection for this merchant."
            )
            return None

        log.info("  Navigating to Business Hours Settings page...")
        driver.get(
            "https://partner.shopee.co.id/settings/shopee-food/business-hours-settings"
        )
        log.info("  Waiting for initial API call...")
        initial_request = driver.wait_for_request(api_pattern, timeout=45)

        if start_page == 1:
            if initial_request.response:
                response_json = parse_response_json(initial_request.response)

                if response_json and response_json.get("code") != 0:
                    log.error(
                        f"  Initial API call failed with error: {response_json.get('msg')}. Cooldown and retry.",
                    )
                    time.sleep(300)
                    return collect_shopee_raw_data(browser_session, merchant_name)

                data = response_json.get("data", {})
                initial_stores = data.get("store_basic_info_list", [])
                all_stores.extend(initial_stores)
                log.info(
                    f"  Page 1 (initial load): Found {len(initial_stores)} stores.",
                )

            with open(temp_file_path, "w") as f:
                json.dump({"last_page": 1, "stores": all_stores}, f)

        # --- Ensure Page Size is 50 ---
        try:
            log.info("  Checking if page size is already set to 50...")
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//span[contains(@class, 'pageSizeItem') and contains(@class, 'active') and .//span[text()='50']]",
                    )
                )
            )
            log.info("  Page size is already 50. No action needed.")
        except TimeoutException:
            log.info("  Page size is not 50. Attempting to set it...")
            try:
                fifty_per_page_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//span[contains(@class, 'pageSizeItem') and .//span[text()='50']]",
                        )
                    )
                )
                del driver.requests
                fifty_per_page_button.click()
                log.info("  Waiting for API call after resizing page...")
                resize_request = driver.wait_for_request(api_pattern, timeout=30)

                if resize_request.response:
                    body_bytes = resize_request.response.body
                    response_text = (
                        gzip.decompress(body_bytes).decode("utf-8")
                        if resize_request.response.headers.get("Content-Encoding")
                        == "gzip"
                        else body_bytes.decode("utf-8")
                    )
                    response_json = json.loads(response_text)
                    if response_json.get("code") == 0:
                        if start_page == 1:
                            data = response_json.get("data", {})
                            all_stores = data.get("store_basic_info_list", [])
                            log.info(
                                f"  Page size set to 50. Page 1 now has {len(all_stores)} stores.",
                            )
                            with open(temp_file_path, "w") as f:
                                json.dump({"last_page": 1, "stores": all_stores}, f)
                    else:
                        log.warning(
                            f"  API call after resize failed: {response_json.get('msg')}",
                        )
            except TimeoutException:
                log.warning(
                    "  Could not find or click the '50 per page' button. Continuing with default size.",
                )

        # --- Resume Jump ---
        if start_page > 1:
            log.info(f"  Attempting to resume by jumping to page {start_page}...")
            if not jump_to_page(driver, wait, start_page):
                log.error("  Could not jump to resume page. Aborting.")
                return None

        page_count = start_page
        max_hard_retries = 3
        hard_retry_count = 0
        collection_successful = False
        last_page_store_count = 0

        while True:
            if page_count != start_page or (start_page == 1 and hard_retry_count == 0):
                page_count += 1

            log.info(
                f"--- Checking for Page {page_count} (Hard Retries: {hard_retry_count}/{max_hard_retries}) ---",
            )

            try:
                next_page_li = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//li[@title='Next Page']")
                    )
                )
                if next_page_li.get_attribute("aria-disabled") == "true":
                    if (
                        last_page_store_count == 50
                        and hard_retry_count < max_hard_retries
                    ):
                        hard_retry_count += 1
                        log.warning(
                            f"  'Next Page' is disabled, but last page had 50 stores. Suspecting UI glitch. Initiating hard reload (Attempt {hard_retry_count}/{max_hard_retries}).",
                        )
                        driver.refresh()
                        time.sleep(5)
                        if not jump_to_page(driver, wait, page_count):
                            log.critical(
                                "  Could not jump to page after hard reload. Aborting.",
                            )
                            collection_successful = False
                            break
                        continue
                    elif last_page_store_count < 50:
                        log.info(
                            "  'Next Page' button is disabled and last page was partial. All pages collected.",
                        )
                        collection_successful = True
                        break
                    else:
                        log.error(
                            "  'Next Page' is disabled after max retries. Assuming end of pages.",
                        )
                        collection_successful = True
                        break

                hard_retry_count = 0
                del driver.requests
                next_page_li.click()

                log.info(f"  Waiting for API call for page {page_count}...")
                page_request = driver.wait_for_request(api_pattern, timeout=30)

                if not page_request.response:
                    raise TimeoutException("No response.")

                body_bytes = page_request.response.body
                response_text = (
                    gzip.decompress(body_bytes).decode("utf-8")
                    if page_request.response.headers.get("Content-Encoding") == "gzip"
                    else body_bytes.decode("utf-8")
                )
                response_json = json.loads(response_text)

                if response_json.get("code") == 0:
                    data = response_json.get("data", {})
                    new_stores = data.get("store_basic_info_list", [])
                    last_page_store_count = len(new_stores)
                    if new_stores:
                        log.info(
                            f"  Page {page_count}: Found {len(new_stores)} new stores.",
                        )
                        all_stores.extend(new_stores)
                        with open(temp_file_path, "w") as f:
                            json.dump(
                                {"last_page": page_count, "stores": all_stores}, f
                            )
                    else:
                        log.info("  API call returned 0 stores. All pages collected.")
                        collection_successful = True
                        break
                    time.sleep(random.uniform(3.0, 6.0))
                else:
                    log.error(
                        f"  Server error on page {page_count}: {response_json.get('msg')}. Initiating 5-minute cooldown and recovery.",
                    )
                    time.sleep(300)

                    del driver.requests

                    if not jump_to_page(driver, wait, page_count):
                        log.error(
                            f"  Recovery failed. Could not jump to page {page_count}. Stopping.",
                        )
                        collection_successful = False
                        break

                    log.info("  Polling for API call after recovery jump...")
                    recovery_request = None
                    for _ in range(15):
                        recovery_request = next(
                            (
                                r
                                for r in reversed(driver.requests)
                                if api_pattern.search(r.url) and r.response
                            ),
                            None,
                        )
                        if recovery_request:
                            log.info("  Found API request during polling.")
                            break
                        time.sleep(1)

                    if recovery_request:
                        rec_body_bytes = recovery_request.response.body
                        rec_response_text = (
                            gzip.decompress(rec_body_bytes).decode("utf-8")
                            if recovery_request.response.headers.get("Content-Encoding")
                            == "gzip"
                            else rec_body_bytes.decode("utf-8")
                        )
                        rec_response_json = json.loads(rec_response_text)

                        if rec_response_json.get("code") == 0:
                            rec_data = rec_response_json.get("data", {})
                            rec_new_stores = rec_data.get("store_basic_info_list", [])
                            last_page_store_count = len(rec_new_stores)
                            if rec_new_stores:
                                log.info(
                                    f"  Recovery successful. Page {page_count}: Found {len(rec_new_stores)} stores.",
                                )
                                all_stores.extend(rec_new_stores)
                                with open(temp_file_path, "w") as f:
                                    json.dump(
                                        {"last_page": page_count, "stores": all_stores},
                                        f,
                                    )
                            else:
                                log.error(
                                    f"  Recovery failed on page {page_count} (0 stores). Stopping.",
                                )
                                break
                        else:
                            log.error(
                                f"  Recovery attempt failed. Server error after jump: {rec_response_json.get('msg')}.",
                            )
                            if hard_retry_count < max_hard_retries:
                                hard_retry_count += 1
                                log.warning(
                                    f"  Initiating hard reload (Attempt {hard_retry_count}/{max_hard_retries}). Refreshing page...",
                                )
                                driver.refresh()
                                time.sleep(5)
                                if not jump_to_page(driver, wait, page_count):
                                    log.critical(
                                        "  Could not jump to page after hard reload. Aborting.",
                                    )
                                    collection_successful = False
                                    break
                                continue
                            else:
                                log.critical(
                                    "  Max hard retries reached. Aborting process.",
                                )
                                collection_successful = False
                                break
                    else:
                        log.error(
                            "  Recovery failed. Could not find API response after jumping to page. Stopping.",
                        )
                        collection_successful = False
                        break

                    hard_retry_count = 0
                    time.sleep(random.uniform(3.0, 6.0))

            except (TimeoutException, NoSuchElementException):
                log.warning("  Could not find 'Next Page' button or timed out.")
                if last_page_store_count < 50:
                    collection_successful = True
                break

        if collection_successful:
            log.info(f"  Collection complete. Found {len(all_stores)} raw entries.")
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            raw_output_dir = "raw_data"
            os.makedirs(raw_output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"shopeefood_{safe_merchant_name}_{timestamp}.json"
            filepath = os.path.join(raw_output_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(all_stores, f, indent=2, ensure_ascii=False)
            log.info(f"✅ Successfully saved raw data to '{filepath}'.")
            return filepath
        return None

    except Exception as e:
        log.error(f"  An unrecoverable error occurred: {e}")
        return None


def run_raw_extraction(browser_session, merchant_task):
    """
    Entry point for raw data extraction.
    """
    collect_shopee_raw_data(browser_session, merchant_task["output_name"])
