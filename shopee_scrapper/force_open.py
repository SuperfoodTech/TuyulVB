import re
import os
import time
import random
import requests
import json
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from common.logger import get_logger
from common.http_utils import parse_response_json
from dotenv import load_dotenv
from common.notifications import send_discord_notification

log = get_logger("force_open")
log.propagate = False
load_dotenv()
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

MONDAY_BOARD_ID = "5025182611"
MONDAY_URL = "https://api.monday.com/v2"
GROUP_ID = "group_mkys1dmf"
CHECK_COL_ID = "color_mkyfabkn"
CLOSED_REQ_COL_ID = "color_mkz76gas"

# XPath patterns for reliable element location
XPATH_APPLY_BUTTON = (
    "//button[contains(@class, 'filter-button') and .//span[text()='Terapkan']]"
)
XPATH_OPEN_BUTTON = (
    "//button[contains(@class, 'shopee-food-btn') and .//span[text()='Buka Outlet']]"
)
XPATH_CLOSE_BUTTON = "//button[contains(@class, 'shopee-food-btn') and .//span[text()='Tutup Outlet Sementara']]"
XPATH_CLOSE_OPTION_ALL_DAY = "//label[contains(@class, 'shopee-food-radio-wrapper')]//span[text()='Sepanjang Hari']"
XPATH_CONFIRM_BUTTON = (
    "//button[contains(@class, 'shopee-food-btn') and .//span[text()='Konfirmasi']]"
)

# Timing and API constants
API_RESPONSE_TIMEOUT = 15
OPEN_ACTION_TIMEOUT = 10
RETRY_COOLDOWN_SECONDS = 300
RATE_LIMIT_DELAY_MIN = 2
RATE_LIMIT_DELAY_MAX = 5

# Mapping merchant name keywords to Monday column IDs
MERCHANT_COL_MAP = {
    "Foodnesia": "text_mky98wgs",
    "WonderFood": "text_mky9y0ta",
    "Lokarasa": "text_mky9dbc8",
    "DoEat": "text_mky9e619",
}

MERCHANT_SHORT_NAME_COL_MAP = {
    "Foodnesia": "text_mky91zrs",
    "WonderFood": "text_mky9ydg7",
    "Lokarasa": "text_mky9y1z5",
    "DoEat": "text_mky9mhmd",
}


def take_debug_screenshot(driver, store_name, action="unknown"):
    """Take a screenshot for debugging failed actions."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_dir = os.path.join(os.path.dirname(__file__), "debug_screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)

        filename = f"{timestamp}_{store_name}_{action}.png"
        filepath = os.path.join(screenshot_dir, filename)

        driver.save_screenshot(filepath)
        log.warning(f"📸 Debug screenshot saved: {filepath}")
        return filepath
    except Exception as e:
        log.error(f"Failed to take debug screenshot: {e}")
        return None


def log_page_html(driver, store_name, action="unknown"):
    """Log the page HTML source for debugging failed actions."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_dir = os.path.join(os.path.dirname(__file__), "debug_html")
        os.makedirs(html_dir, exist_ok=True)

        filename = f"{timestamp}_{store_name}_{action}.html"
        filepath = os.path.join(html_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        log.warning(f"📄 Debug HTML saved: {filepath}")
        return filepath
    except Exception as e:
        log.error(f"Failed to log page HTML: {e}")
        return None


def get_monday_items(board_id, group_id):
    """Fetches items from Monday.com board/group."""
    query = """
    query ($boardId: ID!, $groupId: String!) {
      boards (ids: [$boardId]) {
        groups (ids: [$groupId]) {
          items_page (limit: 500) {
            items {
              name
              column_values {
                id
                text
              }
            }
          }
        }
      }
    }
    """
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    data = {
        "query": query,
        "variables": {"boardId": int(board_id), "groupId": group_id},
    }

    try:
        response = requests.post(MONDAY_URL, json=data, headers=headers)
        response.raise_for_status()
        json_data = response.json()
        if "errors" in json_data:
            log.error(f"Monday API errors: {json_data['errors']}")
            return []

        # Handle structure for API 2023-10
        try:
            boards = json_data.get("data", {}).get("boards", [])
            if not boards:
                log.error(f"Board {board_id} not found or access denied.")
                return []

            groups = boards[0].get("groups", [])
            if not groups:
                log.error(f"Group {group_id} not found in board {board_id}.")
                return []

            items = groups[0].get("items_page", {}).get("items", [])
            return items
        except (KeyError, TypeError, IndexError) as e:
            log.error(f"Unexpected Monday API response structure: {e}")
            return []
    except Exception as e:
        log.error(f"Failed to fetch Monday items: {e}")
        return []


def run_force_open(session, merchant_task, scale_level=1, dry_run=False):
    log.info(f"Starting Force Open/Close Task. Scale Level: {scale_level}")

    # 1. Identify Column for current merchant
    merchant_name = merchant_task.get("output_name", "")
    target_long_col_id = None
    target_short_col_id = None

    for key, col_id in MERCHANT_COL_MAP.items():
        if key.lower() in merchant_name.lower():
            target_long_col_id = col_id
            target_short_col_id = MERCHANT_SHORT_NAME_COL_MAP.get(key)
            break

    if not target_long_col_id:
        log.warning(
            f"Could not map merchant '{merchant_name}' to a Monday column. Skipping."
        )
        return

    # 2. Fetch and Filter Monday Data
    log.info(f"Fetching data from Monday.com for {merchant_name}...")
    items = get_monday_items(MONDAY_BOARD_ID, GROUP_ID)

    stores_to_process = []

    for item in items:
        col_vals = {cv["id"]: cv["text"] for cv in item["column_values"]}

        # Check Status (Yes X)
        status_val = col_vals.get(CHECK_COL_ID) or ""
        if not status_val or not status_val.startswith("Yes "):
            continue

        try:
            # Extract number from "Yes 1", "Yes 2", etc.
            level = int(status_val.split(" ")[1])
            if level <= scale_level:
                # Get the S Long Name and Short Name
                s_long_name = col_vals.get(target_long_col_id) or ""
                s_short_name = col_vals.get(target_short_col_id) or ""

                # Fallback to long name if short name is missing
                if not s_short_name.strip():
                    s_short_name = s_long_name

                # Determine Action (Open or Close)
                closed_req_val = col_vals.get(CLOSED_REQ_COL_ID) or ""
                closed_req_val = closed_req_val.strip()

                action = "OPEN"
                if closed_req_val == "Closed":
                    action = "CLOSE"

                if s_long_name and s_long_name.strip():
                    stores_to_process.append(
                        {
                            "long_name": s_long_name.strip(),
                            "short_name": s_short_name.strip(),
                            "action": action,
                        }
                    )
        except (IndexError, ValueError):
            continue

    log.info(f"Found {len(stores_to_process)} stores to process for {merchant_name}.")

    if not stores_to_process:
        return

    stats = {
        "already_open": [],
        "forced_open": [],
        "already_closed": [],
        "forced_closed": [],
        "failed": [],
        "closed_for_hours": [],  # Stores that are 'Tutup' (normal hours) when we want to Open
    }

    # 3. Shopee Automation
    driver = session.driver
    wait = session.wait

    base_url = (
        "https://partner.shopee.co.id/settings/shopee-food/business-hours-settings"
    )
    api_pattern = re.compile(r"foody\.shopee\.co\.id/api/seller/stores/search")
    open_api_pattern = re.compile(
        r"foody\.shopee\.co\.id/api/seller/store/opening-status/action/open"
    )
    pause_api_pattern = re.compile(
        r"foody\.shopee\.co\.id/api/seller/store/opening-status/action/pause"
    )

    # Helper function for robust API waiting
    def wait_for_api_response(driver, pattern_regex, timeout=10):
        end_time = time.time() + timeout
        while time.time() < end_time:
            # Check requests in reverse order to find the latest one
            for request in reversed(driver.requests):
                if re.search(pattern_regex, request.url):
                    if request.response:
                        return request
            time.sleep(0.5)
        return None

    # 1. Navigate to List (Once at start)
    driver.get(base_url)

    # Ensure we're still logged in
    if not session.ensure_logged_in():
        log.error("Session expired during navigation. Cannot proceed.")
        return stats  # Return empty stats structure

    for i, store_data in enumerate(stores_to_process):
        store_name = store_data["long_name"]
        short_name = store_data["short_name"]
        action = store_data["action"]

        log.info(
            f"[{i+1}/{len(stores_to_process)}] Processing store: {store_name} | Action: {action}"
        )

        # Periodic login check
        if i % 10 == 0 and i > 0:
            if not session.ensure_logged_in():
                log.error(f"Session expired. Stopping.")
                for remaining in stores_to_process[i:]:
                    stats["failed"].append(
                        f"{remaining['long_name']} (Session expired)"
                    )
                break

        try:
            # 2. Search for Store
            log.info(f"Searching for store: {store_name}")
            search_input = wait.until(
                EC.visibility_of_element_located((By.ID, "storeName"))
            )
            time.sleep(1)
            search_input.click()
            search_input.send_keys(Keys.CONTROL + "a")
            search_input.send_keys(Keys.BACKSPACE)
            search_input.send_keys(store_name)
            time.sleep(0.5)

            # Click Apply
            apply_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, XPATH_APPLY_BUTTON))
            )
            apply_btn.click()

            time.sleep(0.5)

            # Wait for results
            try:
                store_xpath = f"//div[contains(@class, 'breakAll') and normalize-space(text())='{store_name}']"
                WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.XPATH, store_xpath))
                )
                log.info(f"Store found.")
            except TimeoutException:
                try:
                    short_wait = WebDriverWait(driver, 2)
                    short_wait.until(
                        EC.visibility_of_element_located(
                            (
                                By.XPATH,
                                "//div[@class='noData']//span[contains(text(), 'Tidak dapat menemukan Toko')]",
                            )
                        )
                    )
                    log.warning(f"Store '{store_name}' not found.")
                    stats["failed"].append(store_name)
                    continue
                except TimeoutException:
                    log.warning(f"Search results unclear for '{store_name}'.")
                    take_debug_screenshot(driver, store_name, "search_unclear")
                    stats["failed"].append(store_name)
                    continue

            # 3. Check Status and Decide
            clicked_into_detail = False
            should_perform_action = False

            # Helper to check status in row
            row_xpath = f"//tr[contains(@class, 'shopee-food-table-row')][.//div[contains(@class, 'breakAll') and normalize-space(text())='{store_name}']]"

            try:
                rows = driver.find_elements(By.XPATH, row_xpath)
                if rows:
                    status_spans = rows[0].find_elements(
                        By.XPATH, ".//span[@class='shopee-food-badge-status-text']/span"
                    )
                    if status_spans and status_spans[0].is_displayed():
                        status_text = status_spans[0].text.strip()
                        log.info(f"Current Status: {status_text}")

                        if action == "OPEN":
                            if status_text == "Buka":
                                log.info("Store already Open. Skipping.")
                                stats["already_open"].append(short_name)
                            elif status_text == "Tutup":
                                log.info(
                                    "Store is 'Tutup' (normal hours). Cannot force open."
                                )
                                stats["closed_for_hours"].append(short_name)
                            elif status_text == "Tutup Sementara":
                                should_perform_action = True
                            else:
                                # Unknown status, try to open
                                should_perform_action = True

                        elif action == "CLOSE":
                            if status_text == "Tutup Sementara":
                                log.info("Store already Force Closed. Skipping.")
                                stats["already_closed"].append(short_name)
                            elif status_text == "Buka":
                                should_perform_action = True
                            elif status_text == "Tutup":
                                log.info(
                                    "Store is 'Tutup' (normal hours). Skipping Force Close."
                                )
                                stats["already_closed"].append(short_name)
                            else:
                                should_perform_action = True
            except Exception as e:
                log.warning(f"Status check failed: {e}")
                # If check fails, try to perform action anyway
                should_perform_action = True

            if not should_perform_action:
                continue

            # 4. Perform Action
            store_element = driver.find_element(By.XPATH, store_xpath)
            store_element.click()
            clicked_into_detail = True
            log.info("Entered detail page.")
            time.sleep(1)

            if not dry_run:
                try:
                    if action == "OPEN":
                        btn = wait.until(
                            EC.element_to_be_clickable((By.XPATH, XPATH_OPEN_BUTTON))
                        )

                        # Clear requests BEFORE clicking
                        del driver.requests
                        btn.click()

                        # Validation
                        try:
                            # Verify API using polling
                            request = wait_for_api_response(
                                driver, open_api_pattern, timeout=OPEN_ACTION_TIMEOUT
                            )
                            if request and request.response and request.response.body:
                                res = parse_response_json(request.response)
                                if res.get("code") == 0:
                                    log.info(f"✅ Forced Open Success (API).")
                                    stats["forced_open"].append(short_name)
                                else:
                                    log.warning(f"API Error: {res.get('msg')}")
                                    stats["failed"].append(f"{store_name} (API Error)")
                            else:
                                raise TimeoutException("No response body")
                        except TimeoutException:
                            # Backup UI
                            log.warning("API timeout, checking UI...")
                            try:
                                WebDriverWait(driver, 5).until(
                                    EC.visibility_of_element_located(
                                        (
                                            By.XPATH,
                                            "//span[contains(text(), 'Buka') and contains(@style, 'rgb(48, 181, 102)')]",
                                        )
                                    )
                                )
                                log.info("✅ Forced Open Success (UI).")
                                stats["forced_open"].append(short_name)
                            except:
                                log.error("❌ Failed to open.")
                                stats["failed"].append(f"{store_name} (Failed)")
                                take_debug_screenshot(driver, store_name, "open_failed")

                    elif action == "CLOSE":
                        # 1. Click "Tutup Outlet Sementara"
                        close_btn = wait.until(
                            EC.element_to_be_clickable((By.XPATH, XPATH_CLOSE_BUTTON))
                        )
                        close_btn.click()

                        # 2. Select "Sepanjang Hari"
                        option = wait.until(
                            EC.element_to_be_clickable(
                                (By.XPATH, XPATH_CLOSE_OPTION_ALL_DAY)
                            )
                        )
                        option.click()

                        # 3. Confirm
                        confirm_btn = wait.until(
                            EC.element_to_be_clickable((By.XPATH, XPATH_CONFIRM_BUTTON))
                        )

                        # Clear requests BEFORE confirm click
                        del driver.requests
                        confirm_btn.click()

                        # Validation
                        try:
                            # Verify API using polling
                            request = wait_for_api_response(
                                driver, pause_api_pattern, timeout=OPEN_ACTION_TIMEOUT
                            )
                            if request and request.response and request.response.body:
                                res = parse_response_json(request.response)
                                if res.get("code") == 0:
                                    log.info(f"✅ Forced Close Success (API).")
                                    stats["forced_closed"].append(short_name)
                                else:
                                    log.warning(f"API Error: {res.get('msg')}")
                                    stats["failed"].append(f"{store_name} (API Error)")
                            else:
                                raise TimeoutException("No response body")
                        except TimeoutException:
                            # Backup UI
                            log.warning("API timeout, checking UI...")
                            try:
                                # Red badge "Tutup Sementara"
                                WebDriverWait(driver, 5).until(
                                    EC.visibility_of_element_located(
                                        (
                                            By.XPATH,
                                            "//span[contains(text(), 'Tutup Sementara') and contains(@style, 'rgb(238, 44, 74)')]",
                                        )
                                    )
                                )
                                log.info("✅ Forced Close Success (UI).")
                                stats["forced_closed"].append(short_name)
                            except:
                                log.error("❌ Failed to close.")
                                stats["failed"].append(f"{store_name} (Failed)")
                                take_debug_screenshot(
                                    driver, store_name, "close_failed"
                                )

                except (TimeoutException, ElementClickInterceptedException) as e:
                    log.error(f"Interaction failed: {e}")
                    stats["failed"].append(store_name)
                    take_debug_screenshot(driver, store_name, "interaction_error")
            else:
                log.info(f"[DRY RUN] Would perform {action} on {store_name}")
                if action == "OPEN":
                    stats["forced_open"].append(f"{short_name} (Dry Run)")
                else:
                    stats["forced_closed"].append(f"{short_name} (Dry Run)")

            # Go back
            if clicked_into_detail:
                driver.get(base_url)
                session.ensure_logged_in()

            time.sleep(random.uniform(RATE_LIMIT_DELAY_MIN, RATE_LIMIT_DELAY_MAX))

        except Exception as e:
            log.error(f"Error processing {store_name}: {e}")
            stats["failed"].append(store_name)
            driver.get(base_url)
            session.ensure_logged_in()

    # --- Send Discord Notification ---
    summary_message = (
        f"**Merchant:** {merchant_name}\n"
        f"**Total Processed:** {len(stores_to_process)}"
    )

    def format_field_value(items, max_items=15):
        if not items:
            return "None"
        if len(items) <= max_items:
            return "\n".join(items)
        remaining = len(items) - max_items
        return "\n".join(items[:max_items]) + f"\n... and {remaining} more"

    fields = []

    # Define categories to check
    categories = [
        ("✅ Forced Open", stats["forced_open"]),
        ("✅ Forced Close", stats["forced_closed"]),
        ("ℹ️ Already Open", stats["already_open"]),
        ("ℹ️ Already Closed", stats["already_closed"]),
        ("⚠️ Closed (Hours)", stats["closed_for_hours"]),
        ("❌ Failed", stats["failed"]),
    ]

    for name, items in categories:
        if items:  # Only add field if there are items
            fields.append(
                {
                    "name": f"{name} ({len(items)})",
                    "value": format_field_value(items),
                    "inline": False,
                }
            )

    if stats["forced_open"] or stats["forced_closed"] or stats["failed"]:
        send_discord_notification(
            DISCORD_WEBHOOK_URL,
            f"Shopee Force Open/Close Report {'(DRY RUN)' if dry_run else ''}",
            summary_message,
            fields=fields,
            color=5814783 if not stats["failed"] else 15158332,
        )
    return stats
