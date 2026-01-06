import json
import time
import random
import os
import shutil
import gzip
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import re

try:
    # Assuming this script is run from the `shopee_scraper` directory
    from modules.shopee.browser_session import BrowserSession, log

    # Refactored to use common modules
    from common.monday_api import execute_monday_query
    from common.shopee_utils import get_current_merchant_name, switch_merchant
    from common.http_utils import parse_response_json
    from config.credentials_shopee import ACCOUNT_CREDS
    from config.settings_shopee import (
        MERCHANT_PROCESSING_LIST,
        MONDAY_BOARD_ID,
        GROUP_MAPPING,
    )
except ImportError:
    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [FATAL] Ensure `credentials.py` and `settings.py` are created and configured."
    )
    exit()


# --- CORRECTED: Data collection with robust scrolling ---
def collect_short_names(browser_session):
    all_stores = []
    api_pattern = re.compile(
        r"api\.partner\.shopee\.co\.id/nb/mss/web-api/PartnerServer/GetStoreList"
    )
    driver = browser_session.driver
    wait = browser_session.wait
    try:
        # NEW: Ensure we are logged in before proceeding
        if not browser_session.ensure_logged_in():
            log.critical(
                "  Failed to ensure login. Aborting collection for this merchant."
            )
            return None

        log.info("  Navigating to the main dashboard...")
        driver.get("https://partner.shopee.co.id/food/dashboard")
        time.sleep(random.uniform(2, 4))
        log.info("  Clicking the dropdown...")
        del driver.requests
        dropdown_trigger = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ant-select-selector"))
        )
        dropdown_trigger.click()
        scrollable_div = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, 'div[style*="max-height: 300px"]')
            )
        )

        last_height = 0
        while True:
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div
            )
            log.info("  Scrolled down in the dropdown...")
            time.sleep(2)
            new_height = driver.execute_script(
                "return arguments[0].scrollHeight", scrollable_div
            )
            if new_height == last_height:
                log.info(
                    "  Scroll height did not change. Reached the end of the list.",
                )
                break
            last_height = new_height

        for request in driver.requests:
            if api_pattern.search(request.url) and request.response:
                response_json = parse_response_json(request.response)
                if response_json:
                    new_stores = response_json.get("data", {}).get("list", [])
                    if new_stores:
                        all_stores.extend(new_stores)

        # The logger doesn't have a 'success' level by default, using 'info'
        log.info(f"✅ Total data collection complete. Found {len(all_stores)} stores.")
        if all_stores:
            final_df = pd.DataFrame(all_stores).drop_duplicates(subset=["storeId"])
            return final_df.to_dict("records")
        return []
    except Exception as e:
        log.error(f"  An unrecoverable error occurred during data collection: {e}")
        return None


# --- CORRECTED: Monday.com upload function with BATCH updates ---
def update_short_names_on_monday(board_id, group_id, stores_data):
    log.info(
        f"Updating {len(stores_data)} short names on Monday.com board '{board_id}'..."
    )
    store_id_column = "text_mkvc896g"
    short_name_column = "text_mkwdygde"

    log.info(
        f"  Fetching ALL existing items from group '{group_id}' (using pagination)..."
    )
    existing_items_map = {}
    next_cursor = None

    while True:
        cursor_arg = f', cursor: "{next_cursor}"' if next_cursor else ""
        query = f'query($boardId: [ID!], $groupId: [String!]) {{ boards(ids:$boardId) {{ groups(ids:$groupId) {{ items_page(limit: 500{cursor_arg}) {{ cursor items {{ id name column_values(ids:["{store_id_column}"]) {{ text }} }} }} }} }} }}'
        variables = {"boardId": [board_id], "groupId": [group_id]}
        response = execute_monday_query(query, variables)

        try:
            items_page_data = response["data"]["boards"][0]["groups"][0]["items_page"]
            items = items_page_data.get("items", [])
            next_cursor = items_page_data.get("cursor")

            for item in items:
                if item.get("column_values") and item["column_values"][0].get("text"):
                    existing_items_map[item["column_values"][0]["text"]] = item["id"]

            log.info(
                f"  -> Fetched {len(items)} items on this page. Total fetched so far: {len(existing_items_map)}"
            )

            if not next_cursor:
                log.info("  All pages fetched.")
                break

        except (KeyError, IndexError, TypeError, AttributeError):
            log.error(
                "  Could not parse existing items from Monday.com during fetch. Stopping pagination."
            )
            break

        time.sleep(0.5)  # Be respectful of API limits between page requests

    log.info(
        f"  Finished fetching. Found a total of {len(existing_items_map)} existing items to match against."
    )

    items_to_update = []
    for store in stores_data:
        store_id = str(store.get("storeId", ""))
        if store_id in existing_items_map:
            items_to_update.append(store)
        else:
            log.warning(
                f"  Skipping Store ID {store_id} ('{store.get('storeName')}') as it was not found on the Monday.com board."
            )

    batch_size = 50
    for i in range(0, len(items_to_update), batch_size):
        batch = items_to_update[i : i + batch_size]
        log.info(
            f"  Updating batch {i//batch_size + 1} of {(len(items_to_update) + batch_size - 1)//batch_size}..."
        )

        mutation_parts, variables, variable_definitions = [], {}, []
        for j, store in enumerate(batch):
            store_id = str(store.get("storeId", ""))
            short_name = store.get("storeName", "Unnamed Store")
            monday_item_id = int(existing_items_map[store_id])

            column_values = {short_name_column: short_name}

            # Define unique variable names for this item in the batch
            item_id_var, board_id_var, value_var = (
                f"itemId{j}",
                f"boardId{j}",
                f"value{j}",
            )

            # Define the types for the mutation signature
            variable_definitions.extend(
                [
                    f"${item_id_var}: ID!",
                    f"${board_id_var}: ID!",
                    f"${value_var}: JSON!",
                ]
            )

            # Build the mutation part for this specific item
            mutation_parts.append(
                f"update_{j}: change_multiple_column_values(board_id: ${board_id_var}, item_id: ${item_id_var}, column_values: ${value_var}) {{ id }}"
            )

            # Add the actual data to the variables dictionary
            variables.update(
                {
                    item_id_var: monday_item_id,
                    board_id_var: board_id,
                    value_var: json.dumps(column_values),
                }
            )

        if mutation_parts:
            full_mutation = f"mutation({', '.join(variable_definitions)}) {{ {' '.join(mutation_parts)} }}"
            result = execute_monday_query(full_mutation, variables)
            if not result:
                log.error(f"  Batch {i//batch_size + 1} failed to update.")
            time.sleep(1.5)  # Pause between batch requests

    log.info("✅ Monday.com board update process complete.")


def run_short_names_sync(browser_session, merchant_task):
    """
    The core logic for syncing short names for a single merchant.
    This function is called by the main_runner.
    """
    group_id = GROUP_MAPPING.get(merchant_task["output_name"])
    if not group_id:
        log.error(
            f"No Group ID found in settings.py for '{merchant_task['output_name']}'. Skipping."
        )
        return

    portal_data = collect_short_names(browser_session)

    if portal_data:
        update_short_names_on_monday(MONDAY_BOARD_ID, group_id, portal_data)
    else:
        log.error(f"No data collected for {merchant_task['validate_name']}.")
