"""
Script to force open stores on Shopee based on Monday.com configuration.
Phase 1: Validate data from Monday (Scale Level logic).
Phase 2: Filter Shopee stores by 'Tutup Sementara'.
Phase 3: Force open specific stores.
"""

import re
import os
import time
import random
import requests
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
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

# XPath patterns for reliable element location
XPATH_APPLY_BUTTON = (
    "//button[contains(@class, 'filter-button') and .//span[text()='Terapkan']]"
)
XPATH_OPEN_BUTTON = (
    "//button[contains(@class, 'shopee-food-btn') and .//span[text()='Buka Outlet']]"
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
    """
    Main execution function for forcing open stores on Shopee.

    Fetches store names from Monday.com based on Scale Level status,
    searches for stores in Shopee merchant portal, and forces them open.

    Args:
        session: BrowserSession object with initialized Selenium driver and WebDriverWait
        merchant_task: Dict containing 'output_name' key with merchant name to match
        scale_level: Integer level (1-N) - only opens stores with status <= this level
        dry_run: If True, logs actions without actually clicking buttons

    Returns:
        None. Updates Discord notification with results (forced_open, already_open, failed)

    Raises:
        No explicit exceptions - errors are logged and handled per store
    """
    log.info(f"Starting Force Open Task. Scale Level: {scale_level}")

    # 1. Identify Column for current merchant
    merchant_name = merchant_task.get("output_name", "")
    target_col_id = None
    for key, col_id in MERCHANT_COL_MAP.items():
        if key.lower() in merchant_name.lower():
            target_col_id = col_id
            break

    if not target_col_id:
        log.warning(
            f"Could not map merchant '{merchant_name}' to a Monday column. Skipping."
        )
        return

    # 2. Fetch and Filter Monday Data
    log.info(f"Fetching data from Monday.com for {merchant_name}...")
    items = get_monday_items(MONDAY_BOARD_ID, GROUP_ID)

    stores_to_open = []
    for item in items:
        col_vals = {cv["id"]: cv["text"] for cv in item["column_values"]}

        # Check Status (Yes X)
        status_val = col_vals.get(CHECK_COL_ID, "")
        if not status_val or not status_val.startswith("Yes "):
            continue

        try:
            # Extract number from "Yes 1", "Yes 2", etc.
            level = int(status_val.split(" ")[1])
            if level <= scale_level:
                # Get the S Long Name
                s_long_name = col_vals.get(target_col_id)
                if s_long_name:
                    stores_to_open.append(s_long_name.strip())
        except (IndexError, ValueError):
            continue

    log.info(
        f"Found {len(stores_to_open)} stores to check/open for {merchant_name} (Scale <= {scale_level})."
    )
    if not stores_to_open:
        return

    stats = {"already_open": [], "forced_open": [], "failed": []}

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

    # 1. Navigate to List (Once at start)
    driver.get(base_url)

    for i, store_name in enumerate(stores_to_open):
        log.info(f"[{i+1}/{len(stores_to_open)}] Processing store: {store_name}")

        for attempt in range(3):  # Retry loop for server errors
            try:
                if attempt > 0:
                    driver.get(base_url)

                # 2. Search for Store
                try:
                    log.info(f"Searching for store: {store_name}")
                    search_input = wait.until(
                        EC.visibility_of_element_located((By.ID, "storeName"))
                    )
                    search_input.click()
                    # Clear input field efficiently using built-in .clear() method
                    search_input.clear()
                    search_input.send_keys(store_name)
                    time.sleep(0.5)

                    # Click Apply
                    apply_btn = wait.until(
                        EC.element_to_be_clickable((By.XPATH, XPATH_APPLY_BUTTON))
                    )
                    apply_btn.click()

                    # Clear old requests AFTER clicking, but BEFORE waiting for response
                    del driver.requests

                    # Wait for API response to ensure table reloads
                    search_request = driver.wait_for_request(
                        api_pattern, timeout=API_RESPONSE_TIMEOUT
                    )

                    if search_request.response:
                        response_json = parse_response_json(search_request.response)

                        if response_json and response_json.get("code") != 0:
                            log.warning(
                                f"Server error detected: {response_json.get('msg')}. Waiting 5 minutes before retrying..."
                            )
                            time.sleep(300)
                            continue

                    time.sleep(1)  # Brief buffer for UI rendering
                except Exception as e:
                    log.error(f"Search failed for {store_name}: {e}")
                    stats["failed"].append(store_name)
                    break

                # 3. Find and Click Store Name
                clicked_into_detail = False
                is_already_open = False
                try:
                    store_xpath = f"//div[contains(@class, 'breakAll') and normalize-space(text())='{store_name}']"
                    store_element = wait.until(
                        EC.element_to_be_clickable((By.XPATH, store_xpath))
                    )

                    # Validate Status: Check if already "Buka"
                    try:
                        # Find the row containing the store name and check for "Buka" status
                        row_xpath = f"//div[contains(@class, 'table-row') or contains(@class, 'list-item')][.//div[contains(@class, 'breakAll') and normalize-space(text())='{store_name}']]"
                        rows = driver.find_elements(By.XPATH, row_xpath)

                        if rows:
                            # Check for "Buka" text inside the row
                            if rows[0].find_elements(
                                By.XPATH, ".//span[text()='Buka']"
                            ):
                                log.info(
                                    f"Store '{store_name}' is already 'Buka'. Skipping."
                                )
                                stats["already_open"].append(store_name)
                                is_already_open = True
                    except Exception as e:
                        log.warning(f"Status validation failed for {store_name}: {e}")

                    # Skip to next store if already open
                    if is_already_open:
                        continue

                    store_element.click()
                    clicked_into_detail = True
                    log.info(
                        f"Clicked store '{store_name}'. Waiting for detail page..."
                    )
                except TimeoutException:
                    log.warning(f"Store '{store_name}' not found in search results.")
                    stats["failed"].append(store_name)
                    break

                # 4. Click "Buka Outlet"
                try:
                    btn = wait.until(
                        EC.element_to_be_clickable((By.XPATH, XPATH_OPEN_BUTTON))
                    )

                    if not dry_run:
                        btn.click()

                        # Clear old requests AFTER clicking, but BEFORE waiting for response
                        del driver.requests

                        # Validate Success via API Response
                        try:
                            open_request = driver.wait_for_request(
                                open_api_pattern, timeout=OPEN_ACTION_TIMEOUT
                            )
                            if open_request.response:
                                response_json = parse_response_json(
                                    open_request.response
                                )
                                if (
                                    response_json is not None
                                    and response_json.get("code") == 0
                                ):
                                    log.info(f"✅ SUCCESS: Store {store_name} opened.")
                                    stats["forced_open"].append(store_name)
                                elif response_json is not None:
                                    msg = response_json.get("msg", "Unknown error")
                                    log.warning(f"API Error for {store_name}: {msg}")
                                    stats["failed"].append(f"{store_name} (API: {msg})")
                                else:
                                    log.warning(
                                        f"Invalid JSON response for {store_name}"
                                    )
                                    stats["failed"].append(
                                        f"{store_name} (Invalid Response)"
                                    )
                            else:
                                log.warning(f"No response received for {store_name}")
                                stats["failed"].append(f"{store_name} (No Response)")
                        except TimeoutException:
                            log.warning(
                                f"Store {store_name} clicked, but API request timed out."
                            )
                            stats["failed"].append(f"{store_name} (Timeout)")
                        time.sleep(1)
                    else:
                        log.info(
                            f"[DRY RUN] Would click 'Buka Outlet' for {store_name}"
                        )
                        stats["forced_open"].append(f"{store_name} (Dry Run)")

                except TimeoutException:
                    log.warning(f"'Buka Outlet' button not found for {store_name}.")
                    stats["failed"].append(store_name)

                # Navigate back to list page if we entered the detail page
                if clicked_into_detail:
                    driver.get(base_url)

                # Rate limiting between stores to avoid API throttling
                time.sleep(random.uniform(RATE_LIMIT_DELAY_MIN, RATE_LIMIT_DELAY_MAX))

                break  # Success, exit retry loop

            except Exception as e:
                log.error(f"Error processing store {store_name}: {e}")
                stats["failed"].append(store_name)
                break
        else:
            log.error(f"Max retries reached for {store_name}.")
            stats["failed"].append(store_name)

    # --- Send Discord Notification ---
    summary_message = (
        f"**Merchant:** {merchant_name}\n" f"**Total Processed:** {len(stores_to_open)}"
    )

    fields = [
        {
            "name": f"✅ Forced Open ({len(stats['forced_open'])})",
            "value": (
                "\n".join(stats["forced_open"]) if stats["forced_open"] else "None"
            ),
            "inline": False,
        },
        {
            "name": f"ℹ️ Already Open ({len(stats['already_open'])})",
            "value": (
                "\n".join(stats["already_open"]) if stats["already_open"] else "None"
            ),
            "inline": False,
        },
        {
            "name": f"❌ Failed ({len(stats['failed'])})",
            "value": "\n".join(stats["failed"]) if stats["failed"] else "None",
            "inline": False,
        },
    ]

    send_discord_notification(
        DISCORD_WEBHOOK_URL,
        f"Shopee Force Open Report {'(DRY RUN)' if dry_run else ''}",
        summary_message,
        fields=fields,
        color=5814783 if not stats["failed"] else 15158332,  # Blue or Red
    )
