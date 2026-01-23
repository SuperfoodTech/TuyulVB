import json
import time
from datetime import datetime
import os
import socket
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
)
from tqdm import tqdm
import sys  # noqa

# Load environment variables from .env file
# --- Setup Project Path ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.monday_api import execute_monday_query

# --- Import configurations from separate config files ---
from config.credentials_grab import ACCOUNT_CREDS

try:
    import grab_scrapper.config.settings as settings

    # Validate that all required settings are present
    required_settings = [
        "GRAB_MERCHANT_CONFIG",
        "TARGET_API_URL",
        "SINGLE_OUTLET_CHECK_URL",
        "MONDAY_BOARD_ID",
        "MONDAY_TARGET_GROUP",
        "SAVE_RAW_DATA_FOR_DEBUG",
    ]
    for setting_name in required_settings:
        if not hasattr(settings, setting_name):
            raise AttributeError(f"'{setting_name}' is missing from settings.py")
    from config.settings_grab import *  # noqa
except ImportError:
    print("[FATAL] `settings_grab.py` not found. Please create it from the template.")
    exit()
except AttributeError as e:
    print(f"[FATAL] Configuration error: {e}")
    exit()

# --- Helper Functions ---


def log(level, message):
    """Prints a message to the console with a timestamp and log level."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level.upper()}] {message}")


def is_network_available():
    """Checks for an active internet connection."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False


# --- Import shared browser session ---
try:
    from modules.grab.common.session import BrowserSession
except ImportError:
    log("fatal", "BrowserSession class not found in modules/grab/common/session.py")
    exit()


def handle_W_modal(driver):
    """Handles the specific 'Welcome' modal for W-series accounts."""
    try:
        # Wait for the modal to be visible
        modal_close_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(@class, 'ant-modal-close') and .//span[contains(@aria-label, 'Close')]]",
                )
            )
        )
        log("info", "Welcome modal detected. Attempting to close it.")
        modal_close_button.click()
        log("success", "Successfully closed the Welcome modal.")
        time.sleep(2)  # Wait a moment for the UI to settle
    except TimeoutException:
        # If the modal doesn't appear, that's fine. Just log it and continue.
        log("info", "Welcome modal did not appear within the timeout period.")


# --- Data Collection ---


def collect_all_merchants(driver):
    """
    Actively waits for and intercepts API calls to extract merchant data,
    returning both the data and the detected account type. Includes scrolling
    for multi-outlet pagination.
    """
    log("info", "Navigating to the menu page to trigger data loading...")
    # Navigate to the correct page first.
    driver.get(GRAB_MERCHANT_CONFIG["merchant_list_url"])
    # Wait for a known element on the menu page to ensure it's loaded.
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.dui-table"))
    )
    log("info", "Menu page loaded. Starting data collection...")
    del driver.requests
    try:
        request = driver.wait_for_request(TARGET_API_URL, timeout=30)
        log("info", "Multi-outlet API found. Processing initial data...")
        data = json.loads(request.response.body.decode("utf-8"))

        all_merchants = data.get("merchants", [])
        has_more_data = data.get("hasMore", False)

        if not has_more_data:
            log("info", "API indicates all data was collected in the first request.")
            return all_merchants, "MULTI_OUTLET"

        log("info", "More data available, initiating scrolling to load all outlets...")
        try:
            scrollable_element = driver.find_element(
                By.CSS_SELECTOR, "div.dui-table-body"
            )
        except NoSuchElementException:
            log(
                "error",
                "Could not find scrollable element for pagination. Returning initial data only.",
            )
            return all_merchants, "MULTI_OUTLET"

        page_scroll_attempts = 0
        while has_more_data:
            previous_merchant_count = len(all_merchants)
            del driver.requests
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_element
            )

            try:
                scroll_request = driver.wait_for_request(TARGET_API_URL, timeout=60)
                if scroll_request and scroll_request.response:
                    data = json.loads(scroll_request.response.body.decode("utf-8"))
                    merchants_batch = data.get("merchants", [])

                    if merchants_batch:
                        all_merchants.extend(merchants_batch)

                    if len(all_merchants) == previous_merchant_count:
                        page_scroll_attempts += 1
                        if page_scroll_attempts > 2:
                            log(
                                "error",
                                "No new merchants found after multiple scrolls. Stopping pagination.",
                            )
                            break
                    else:
                        page_scroll_attempts = 0

                    has_more_data = data.get("hasMore", False)
            except TimeoutException:
                log(
                    "warn",
                    "Timed out waiting for API response while scrolling. Assuming no more data.",
                )
                break
        return all_merchants, "MULTI_OUTLET"

    except TimeoutException:
        log("info", "Multi-outlet API not found. Checking for single-outlet API...")
        try:
            request = driver.wait_for_request(SINGLE_OUTLET_CHECK_URL, timeout=20)
            log("info", "Single-outlet API found. Processing...")
            if request and request.response:
                merchants = json.loads(request.response.body.decode("utf-8")).get(
                    "merchants", []
                )
                return merchants, "SINGLE_OUTLET"
        except TimeoutException:
            log(
                "error",
                "Did not capture any merchant data API call within the timeout period.",
            )
            return [], "ERROR"

    except (json.JSONDecodeError, NoSuchElementException) as e:
        log("error", f"Failed to get merchant data. Error: {e}")
        return [], "ERROR"

    return [], "ERROR"


# --- Monday.com Integration ---


def save_raw_data_to_json(data, account_name):
    """Saves the raw collected data to a JSON file for debugging."""
    if not data:
        log("info", "No raw data to save.")
        return

    output_dir = os.path.join(os.path.dirname(__file__), "raw_grab_data")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"grabfood_{account_name}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    try:
        log("info", f"Saving raw data for '{account_name}' to '{filepath}'...")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log("success", f"Successfully saved raw data dump.")
    except Exception as e:
        log("error", f"Failed to save raw data dump: {e}")


def count_outlet_statuses(merchants_list):
    """Counts the occurrences of each outlet status from the raw data."""
    if not merchants_list:
        return {}

    status_counts = {}
    for merchant in merchants_list:
        status = merchant.get("status", "Unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    return status_counts


def write_to_monday(merchants_list, board_id, group_id, account_name, api_type):
    """
    Creates or updates items on Monday.com based on scraped Grab data.
    It fetches existing items to avoid creating duplicates.
    """
    # --- Initialize counters for the summary report ---
    created_count = 0
    updated_count = 0
    deleted_count = 0

    log("info", f"Connecting to Monday.com board: {board_id}, group: {group_id}...")

    # Map API status values to Monday.com status labels
    status_map = {
        "ACTIVE": "Active",
        "INACTIVE": "Inactive",
        "RESTRICTED": "Restricted",
        # This new status will be used for stale items
    }

    # 1. Use user-provided, stable column IDs for reliability
    store_id_col = "text_mkvc896g"
    outlet_status_col = "color_mkvztyew"

    # 2. Fetch all existing items from the group to check for duplicates
    log(
        "info",
        f"Fetching ALL existing items from group '{group_id}' (using pagination)...",
    )
    all_monday_items = []  # Will store the full item objects
    next_cursor = None
    item_count = 0

    while True:
        cursor_arg = f', cursor: "{next_cursor}"' if next_cursor else ""
        # Refactored to use a GraphQL variable for the column ID to prevent syntax errors.
        query_items = f"""
            query($boardId: [ID!], $groupId: [String!], $columnId: [String!]) {{
                boards(ids: $boardId) {{
                    groups(ids: $groupId) {{
                        items_page(limit: 500{cursor_arg}) {{
                            cursor
                            items {{
                                id
                                name
                                column_values(ids: $columnId) {{
                                    text
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        """
        variables = {
            "boardId": [board_id],
            "groupId": [group_id],
            "columnId": [store_id_col],
        }
        response = execute_monday_query(query_items, variables)

        try:
            items_page_data = response["data"]["boards"][0]["groups"][0]["items_page"]
            items = items_page_data.get("items", [])
            next_cursor = items_page_data.get("cursor")

            all_monday_items.extend(items)
            item_count += len(items)
            log(
                "info",
                f"  -> Fetched {len(items)} items on this page. Total fetched so far: {item_count}",
            )

            if not next_cursor:
                break  # Exit loop if there are no more pages

        except (KeyError, IndexError, TypeError) as e:
            log(
                "warn",
                f"Could not parse existing items during pagination: {e}. Stopping fetch.",
            )
            break
        time.sleep(0.5)  # Be respectful of API limits

    # Create a map of {store_id: monday_item_id} from the fetched items
    # This map only includes items that have a valid store ID.
    existing_items_map = {}
    for item in all_monday_items:
        # Ensure column_values is not empty and the text field exists
        if item.get("column_values") and item["column_values"][0].get("text"):
            existing_items_map[item["column_values"][0]["text"]] = item["id"]

    if existing_items_map:
        log(
            "info",
            f"Found {len(existing_items_map)} existing items to match against.",
        )
    else:
        log("info", "No existing items found in the target group.")

    # Use a function for consistent logging format inside tqdm
    def tqdm_log(level, message):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tqdm.write(f"[{ts}] [{level.upper()}] {message}")

    items_to_create = []
    items_to_update = []

    # 3. Identify and delete stale items BEFORE processing creates/updates.
    log("info", "Checking for stale items (exist on Monday but not in Grab data)...")

    # Create a set of all store IDs from the Grab data for efficient lookup.
    grab_store_ids = {
        str(m.get("merchantID", "")) for m in merchants_list if m.get("merchantID")
    }

    stale_monday_items = []
    active_monday_items = []  # Items that are not stale
    for item in all_monday_items:
        store_id_value = None
        if item.get("column_values") and item["column_values"][0].get("text"):
            store_id_value = item["column_values"][0]["text"]

        if store_id_value not in grab_store_ids:
            stale_monday_items.append(item)
        else:
            active_monday_items.append(item)

    if stale_monday_items and grab_store_ids:
        log(
            "info",
            f"Found {len(stale_monday_items)} stale items to DELETE.",
        )
        with tqdm(
            total=len(stale_monday_items), desc="Deleting stale items", unit="item"
        ) as pbar_delete:
            for item in stale_monday_items:
                monday_item_id = int(item["id"])
                pbar_delete.set_description(f"Deleting item ID: {monday_item_id}")

                mutation = (
                    "mutation ($itemId: ID!) { delete_item (item_id: $itemId) { id } }"
                )
                variables = {"itemId": monday_item_id}

                # Execute the mutation with retry logic
                retry_count = 0
                success = False
                while retry_count < 3:
                    response = execute_monday_query(mutation, variables)
                    if response and "errors" not in response:
                        success = True
                        break

                    error_msg = response.get("errors", [{"message": "Network error"}])[
                        0
                    ]["message"]
                    log("error", f"Failed to delete item {monday_item_id}: {error_msg}")
                    retry_count += 1
                    time.sleep(2)

                if success:
                    deleted_count += 1

                pbar_delete.update(1)
                time.sleep(0.2)
    elif stale_monday_items and not grab_store_ids:
        log(
            "warn",
            f"Found {len(stale_monday_items)} stale items, but the Grab data is empty. Skipping deletion to prevent accidental data loss.",
        )
    else:
        log("info", "No stale items found. All items on Monday.com are accounted for.")

    # 4. Iterate and prepare create/update lists from the remaining active items
    log(
        "info", f"Starting to process {len(merchants_list)} merchants for Monday.com..."
    )

    with tqdm(
        total=len(merchants_list), desc=f"Uploading to {account_name}", unit="item"
    ) as pbar:
        for merchant in merchants_list:
            pbar.set_description(
                f"Processing: {merchant.get('merchantName', '...')[:30]}"
            )

            store_id = str(merchant.get("merchantID", ""))
            if not store_id:
                tqdm_log("warn", "Skipping a merchant with no Store ID.")
                pbar.update(1)
                continue

            item_name = merchant.get("merchantName", "Unnamed Merchant")

            if store_id in existing_items_map:
                # --- UPDATE logic ---
                monday_item_id = int(existing_items_map[store_id])
                if SAVE_RAW_DATA_FOR_DEBUG:
                    tqdm_log(
                        "info",
                        f"  -> Found existing item. Preparing UPDATE for Monday ID: {monday_item_id}",
                    )

                update_column_values = {"name": item_name}
                status_value = merchant.get("status")
                if status_value:
                    mapped_status = status_map.get(status_value.upper(), status_value)
                    update_column_values[outlet_status_col] = {"label": mapped_status}

                items_to_update.append(
                    {
                        "itemId": monday_item_id,
                        "colVals": update_column_values,
                    }
                )
            else:
                # --- CREATE logic ---
                if SAVE_RAW_DATA_FOR_DEBUG:
                    tqdm_log(
                        "info",
                        f"  -> New item. Preparing CREATE for Store ID: {store_id}",
                    )
                create_column_values = {store_id_col: store_id}
                status_value = merchant.get("status")
                if status_value:
                    mapped_status = status_map.get(status_value.upper(), status_value)
                    create_column_values[outlet_status_col] = {"label": mapped_status}

                mutation = """
                    mutation ($boardId: ID!, $groupId: String!, $itemName: String!, $colVals: JSON!) {
                        create_item (board_id: $boardId, group_id: $groupId, item_name: $itemName, column_values: $colVals) { id }
                    }
                """
                variables = {
                    "boardId": board_id,
                    "groupId": group_id,
                    "itemName": item_name,
                    "colVals": json.dumps(create_column_values),
                }
                items_to_create.append(
                    {"mutation": mutation, "variables": variables, "name": item_name}
                )

            pbar.update(1)

    # --- 5. Execute Batched Updates ---
    if items_to_update:
        log("info", f"Executing batch updates for {len(items_to_update)} items...")
        updated_count = _execute_batch_update(
            items_to_update, board_id, "Updating items"
        )

    # --- 6. Execute Creations (one by one) ---
    if items_to_create:
        log("info", f"Executing creation for {len(items_to_create)} new items...")
        with tqdm(
            total=len(items_to_create), desc="Creating new items", unit="item"
        ) as pbar_create:
            for item_to_create in items_to_create:
                pbar_create.set_description(f"Creating: {item_to_create['name'][:30]}")
                response = execute_monday_query(
                    item_to_create["mutation"], item_to_create["variables"]
                )
                if response and "errors" not in response:
                    created_count += 1
                else:
                    error_msg = response.get("errors", [{"message": "Unknown"}])[0][
                        "message"
                    ]
                    log(
                        "error",
                        f"Failed to create item '{item_to_create['name']}': {error_msg}",
                    )
                pbar_create.update(1)
                time.sleep(0.2)

    log("success", f"Finished uploading process for account '{account_name}'.")
    return created_count, updated_count, deleted_count


def _execute_batch_update(items_to_update, board_id, pbar_desc):
    """
    Executes batch updates on Monday.com for a list of items.
    `items_to_update` should be a list of dicts, each with 'itemId' and 'colVals'.
    """
    updated_count = 0
    batch_size = 50  # Monday.com's recommended batch size

    with tqdm(
        total=len(items_to_update), desc=pbar_desc, unit="item", leave=False
    ) as pbar:
        for i in range(0, len(items_to_update), batch_size):
            batch = items_to_update[i : i + batch_size]
            pbar.set_description(f"{pbar_desc} (Batch {i//batch_size + 1})")

            # Construct a single GraphQL mutation with multiple operations
            mutation_parts = []
            variables = {"board_id": board_id}
            for index, item in enumerate(batch):
                item_id_var = f"itemId_{index}"
                col_vals_var = f"colVals_{index}"
                variables[item_id_var] = item["itemId"]
                variables[col_vals_var] = json.dumps(item["colVals"])
                mutation_parts.append(
                    f"""
                    update_{index}: change_multiple_column_values(
                        item_id: ${item_id_var},
                        board_id: $board_id,
                        column_values: ${col_vals_var}
                    ) {{ id }}
                """
                )

            # Define the types for all variables at the top of the mutation
            variable_definitions = ", ".join(
                [f"$itemId_{j}: ID!, $colVals_{j}: JSON!" for j in range(len(batch))]
            )
            full_mutation = f"mutation($board_id: ID!, {variable_definitions}) {{ {' '.join(mutation_parts)} }}"

            # Execute the batched mutation with retry logic
            retry_count = 0
            while retry_count < 3:
                response = execute_monday_query(full_mutation, variables)
                if response and "errors" not in response:
                    updated_count += len(batch)
                    break  # Success

                error_msg = response.get("errors", [{"message": "Network error"}])[0][
                    "message"
                ]
                log("error", f"Batch update failed: {error_msg}")
                if "complexity" in error_msg.lower():
                    log("warn", "Complexity limit hit. Pausing for 60s and retrying...")
                    time.sleep(60)
                    retry_count += 1
                else:
                    break  # Non-retriable error

            pbar.update(len(batch))
            time.sleep(1)  # Pause between batches to be respectful of the API
    return updated_count


# --- Main Execution ---
if __name__ == "__main__":
    print("=" * 50)
    print("=== Grab Merchant Data Extractor & Monday.com Uploader ===")
    print("=" * 50)

    browser = BrowserSession(GRAB_MERCHANT_CONFIG)
    if not browser.driver:
        exit()

    while True:
        account_list = list(ACCOUNT_CREDS.keys())
        print("\n" + "=" * 70)
        log("info", "Please select an option:")
        print("     1. Run All Accounts")
        for i, name in enumerate(account_list):
            print(f"     {i+2}. {name}")
        print(f"     {len(account_list) + 2}. Exit")
        print("=" * 70)
        print(f"Enter number (1-{len(account_list) + 2}): ", end="", flush=True)
        choice_input = input()  # Now capture the user's input

        try:
            choice = int(choice_input)
        except ValueError:
            log("error", "Invalid input.")
            continue

        if choice == len(account_list) + 2:
            break

        accounts_to_process = (
            [account_list[choice - 2]]
            if 2 <= choice <= len(account_list) + 1
            else account_list if choice == 1 else []
        )
        if not accounts_to_process:
            log("error", f"Invalid choice '{choice_input}'.")
            continue

        summary_stats = {}

        for account_name in accounts_to_process:
            print("-" * 70)
            log("info", f"--- Starting extraction for account: {account_name} ---")

            target_group_info = next(
                (g for g in MONDAY_TARGET_GROUP if g["source_portal"] == account_name),
                None,
            )
            if not target_group_info:
                log(
                    "error",
                    f"Monday.com group config not found for '{account_name}' in settings.py. Skipping.",
                )
                continue

            # Special handling for 'W' accounts that might have a welcome modal
            if account_name.startswith("W"):
                handle_W_modal(browser.driver)

            try:
                if browser.login(account_name, ACCOUNT_CREDS[account_name]):
                    merchants, api_type = collect_all_merchants(browser.driver)

                    # Save raw data for debugging if the flag is enabled
                    if SAVE_RAW_DATA_FOR_DEBUG:
                        save_raw_data_to_json(merchants, account_name)

                    if merchants:
                        log(
                            "success",
                            f"Data collection complete! Found {len(merchants)} merchants (Type: {api_type}).",
                        )
                        target_group_id = target_group_info["group_id"]
                        created, updated, deleted = write_to_monday(
                            merchants,
                            MONDAY_BOARD_ID,
                            target_group_id,
                            account_name,
                            api_type,
                        )
                        # Count statuses for the summary report
                        status_counts = count_outlet_statuses(merchants)
                    else:
                        created, updated, deleted, status_counts = 0, 0, 0, {}
                        log(
                            "error",
                            f"No merchant data was collected for '{account_name}'.",
                        )

                    summary_stats[account_name] = {
                        "created": created,
                        "updated": updated,
                        "deleted": deleted,
                        "total_found": len(merchants),
                        "status_counts": status_counts,
                    }
            except Exception as e:
                log("fatal", f"An unexpected error occurred for '{account_name}': {e}")
                summary_stats[account_name] = {
                    "created": 0,
                    "updated": 0,
                    "deleted": 0,
                    "error": True,
                    "total_found": 0,
                    "status_counts": {},
                }

        # --- Print Summary Report ---
        if summary_stats:
            print("-" * 70)
            log("info", "--- Batch Execution Summary ---")
            print("-" * 70)
            header = f"{'Account':<15} | {'Found':>7} | {'Created':>9} | {'Updated':>9} | {'Deleted':>9} | {'Total':>7}"
            print(header)
            print("=" * len(header))
            for account, stats in summary_stats.items():
                created = stats.get("created", 0)
                updated = stats.get("updated", 0)
                deleted = stats.get("deleted", 0)
                # Total synced includes created and updated, delisted is a separate action on existing items
                total_synced = created + updated
                total_found = stats.get("total_found", 0)
                error_flag = " (error)" if stats.get("error") else ""
                print(
                    f"{account:<15} | {total_found:>7} | {created:>9} | {updated:>9} | {deleted:>9} | {total_synced:>7}{error_flag}"
                )
                # Print status breakdown
                status_counts = stats.get("status_counts", {})
                if status_counts:
                    status_str = ", ".join(
                        [f"{k}: {v}" for k, v in status_counts.items()]
                    )
                    print(f"  └─ Statuses: {status_str}")

            print("-" * 70)

        log("info", "Batch finished. Returning to main menu.")

    browser.quit()
    log("info", "Process finished.")
