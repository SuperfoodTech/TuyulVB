import json
import time
import random
import asyncio
import requests
import pandas as pd
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

try:
    # Assuming this script is run from the `shopee_scraper` directory
    from modules.shopee.browser_session import BrowserSession, log

    # Refactored to use common modules
    from common.monday_api import execute_monday_query
    from config.settings_shopee import (
        MERCHANT_PROCESSING_LIST,
        MONDAY_BOARD_ID,
        GROUP_MAPPING,
    )

    # from modules.shopee.webshopee_api_client import WebShopeeAPIClient # REMOVED
    from modules.shopee.api_utils import extract_tokens_from_driver, get_shopee_headers
except ImportError as e:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [FATAL] Import error: {e}")
    exit()

# API Configuration
SHOPEE_API_BASE = "https://foody.shopee.co.id"
API_TIMEOUT = 10


def fetch_stores_via_api(tob_token, entity_id):
    """Fetches all stores using the Shopee Partner API (Synchronous)."""
    all_stores = []

    headers = get_shopee_headers(tob_token, entity_id)
    page = 1
    page_size = 50

    log.info(f"🚀 Starting API collection of stores...")

    while True:
        log.info(f"  Fetching Page {page} (Size: {page_size})...")

        payload = {"filter": {}, "page_no": page, "page_size": page_size}

        try:
            url = f"{SHOPEE_API_BASE}/api/seller/stores/search"
            response = requests.post(
                url, json=payload, headers=headers, timeout=API_TIMEOUT
            )

            try:
                data = response.json()
            except json.JSONDecodeError:
                log.error(f"  Failed to parse API response: {response.text[:100]}...")
                break

            if data.get("code") != 0:
                if data.get("code") == 100002 and data.get("msg") == "mis svr err":
                    log.warning(
                        "  Encountered 'mis svr err' (Code 100002). Waiting 5 minutes before retrying..."
                    )
                    time.sleep(300)
                    continue

                log.error(f"  API Error: {data.get('msg')}")
                break

            # Extract list from nested structure
            # Structure matches extract_raw.py: data -> data -> store_basic_info_list
            store_list = data.get("data", {}).get("store_basic_info_list", [])

            if not store_list:
                log.info("  No more stores returned by API. Extraction complete.")
                break

            all_stores.extend(store_list)
            log.info(f"  + {len(store_list)} stores. Total: {len(all_stores)}")

            # Check if we've reached the end based on page size
            if len(store_list) < page_size:
                log.info("  Partial page received. Reached end of list.")
                break

            page += 1
            time.sleep(random.uniform(0.5, 1.0))  # Polite delay

        except requests.exceptions.RequestException as e:
            log.error(f"  Network error during API call: {e}")
            break
        except Exception as e:
            log.error(f"  Unexpected error: {e}")
            break

    return all_stores


def collect_short_names(browser_session):
    """
    Collects short names using the Shopee Partner API.
    Uses the browser session to get valid cookies.
    """
    try:
        # Ensure we are logged in before proceeding
        if not browser_session.ensure_logged_in():
            log.critical(
                "  Failed to ensure login. Aborting collection for this merchant."
            )
            return None

        log.info("  Extracting cookies for API access...")
        tob_token, entity_id = extract_tokens_from_driver(browser_session.driver)

        if not tob_token or not entity_id:
            log.warning("  Cookies not found immediately. Refreshing page to ensure cookies are loaded...")
            browser_session.driver.refresh()
            time.sleep(5)
            tob_token, entity_id = extract_tokens_from_driver(browser_session.driver)

        if not tob_token or not entity_id:
            # Debugging: Log available cookies to understand why it failed
            try:
                available_cookies = [c.get('name') for c in browser_session.driver.get_cookies()]
                log.debug(f"  Available cookies: {available_cookies}")
            except Exception:
                pass
            
            log.error(
                "❌ Failed to find required authentication cookies (shopee_tob_token, shopee_tob_entity_id)."
            )
            return None

        # Run the API fetch synchronously
        # all_stores = asyncio.run(fetch_stores_via_api(tob_token, entity_id)) # REMOVED
        all_stores = fetch_stores_via_api(tob_token, entity_id)

        log.info(f"✅ Total data collection complete. Found {len(all_stores)} stores.")

        if all_stores:
            # Note: store_basic_info_list items have 'store_id' (snake_case) or 'storeId' (camelCase)?
            # extract_raw.py just dumps it.
            # Let's check the API response structure typically.
            # The previous async code used `store.get("storeId")`.
            # The NEW API endpoint used in extract_raw.py (api/seller/stores/search) might return snake_case keys like `store_id`.
            # I will need to inspect the keys or handle both.
            # Let's inspect the first item if available and normalize.

            normalized_stores = []
            for store in all_stores:
                # Normalize key to 'storeId' and 'storeName' for downstream compatibility
                s_id = store.get("store_id") or store.get("storeId")
                s_name = store.get("store_name") or store.get("storeName")
                if s_id:
                    # Create a dict with keys expected by update_short_names_on_monday
                    normalized_stores.append({"storeId": s_id, "storeName": s_name})

            final_df = pd.DataFrame(normalized_stores).drop_duplicates(
                subset=["storeId"]
            )
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
