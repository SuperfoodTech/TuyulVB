import json
import time
import random
import os
import glob
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import re
from dotenv import load_dotenv

try:
    # Assuming this script is run from the `shopee_scraper` directory
    from modules.shopee.browser_session import log

    # Refactored to use common modules
    from common.monday_api import execute_monday_query
    from common.monday_utils import get_board_name
    from common.notifications import send_discord_notification
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

# --- Load Environment Variables for Notifications ---
load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def _handle_stale_entries(board_id, existing_items_map, fresh_store_ids):
    """
    Identifies items on Monday.com that are no longer in the fresh data
    and DELETES them.
    """
    log.info("  Checking for stale entries to delete...")
    stale_store_ids = list(set(existing_items_map.keys()) - fresh_store_ids)

    if not stale_store_ids:
        log.info("  No stale entries found. All items are up-to-date.")
        return

    log.warning(
        f"  Found {len(stale_store_ids)} stale entries on Monday.com that are no longer in the portal data. DELETING them now.",
    )

    # Process stale entries in smaller batches to avoid API complexity limits.
    batch_size = 50
    for i in range(0, len(stale_store_ids), batch_size):
        batch = stale_store_ids[i : i + batch_size]
        log.warning(
            f"  Deleting batch {i//batch_size + 1}/{(len(stale_store_ids) + batch_size - 1)//batch_size} ({len(batch)} items)...",
        )

        mutation_parts, variables, variable_definitions = [], {}, []

        for j, store_id in enumerate(batch):
            item_id = int(existing_items_map[store_id]["id"])

            # Define unique variable names for this item in the batch
            item_id_var = f"itemId{j}"

            # Define the types for the mutation signature
            variable_definitions.append(f"${item_id_var}: ID!")

            # Build the mutation part for this specific item
            mutation_parts.append(
                f"delete_{j}: delete_item(item_id: ${item_id_var}) {{ id }}"
            )

            # Add the actual data to the variables dictionary
            variables[item_id_var] = item_id

        if mutation_parts:
            full_mutation = f"mutation({', '.join(variable_definitions)}) {{ {' '.join(mutation_parts)} }}"
            execute_monday_query(full_mutation, variables)
            time.sleep(1.5)  # Pause between batch requests to be safe

    log.info(f"  Finished processing {len(stale_store_ids)} stale entries.")


def _check_busy_status_against_schedule(store_data):
    """
    Checks if a store's display_status is 'Busy' (3) when it should be open
    according to its regular_hours schedule.

    Returns:
        bool: True if the store is 'Busy' but should be open, False otherwise.
    """
    display_status = store_data.get("display_status")
    regular_hours = store_data.get("regular_hours")

    if display_status != 3 or not regular_hours:
        return False

    try:
        now = datetime.now(ZoneInfo("Asia/Jakarta"))
        current_weekday = now.isoweekday()
        seconds_from_midnight = (
            now - now.replace(hour=0, minute=0, second=0, microsecond=0)
        ).total_seconds()

        # Find today's schedule
        todays_schedule = next(
            (day for day in regular_hours if day.get("weekday") == current_weekday),
            None,
        )

        if not todays_schedule or todays_schedule.get("config_enabled") != 1:
            return False

        # Check all time intervals for today
        for interval in todays_schedule.get("intervals", []):
            start_sec = interval.get("start_relative_sec", 0)
            end_sec = interval.get("end_relative_sec", 0)

            # Check if the current time falls within any open interval
            if start_sec < end_sec and start_sec <= seconds_from_midnight < end_sec:
                start_time_str = time.strftime("%H:%M", time.gmtime(start_sec))
                end_time_str = time.strftime("%H:%M", time.gmtime(end_sec))

                log.warning(
                    f"    -> Flagging 'Busy' status: Store should be open now based on schedule ({start_time_str} - {end_time_str}).",
                )
                return True

    except Exception as e:
        log.error(f"    -> Error while checking busy status: {e}")
        return False

    return False


def upload_to_monday(board_id, group_id, stores_data, portal_name):
    log.info(f"Uploading {len(stores_data)} stores to Monday.com board '{board_id}'...")
    store_id_column = "text_mkvc896g"
    log.info(
        f"  Fetching ALL existing items from group '{group_id}' (using pagination)...",
    )

    existing_items_map = {}
    next_cursor = None
    item_count = 0

    while True:
        cursor_arg = f', cursor: "{next_cursor}"' if next_cursor else ""
        query = f'query($boardId: [ID!], $groupId: [String!]) {{ boards(ids:$boardId) {{ groups(ids:$groupId) {{ items_page(limit: 100{cursor_arg}) {{ cursor items {{ id name column_values(ids:["{store_id_column}"]) {{ text }} }} }} }} }} }}'
        variables = {"boardId": [board_id], "groupId": [group_id]}

        response = execute_monday_query(query, variables)

        try:
            items_page_data = response["data"]["boards"][0]["groups"][0]["items_page"]
            items = items_page_data["items"]
            next_cursor = items_page_data["cursor"]

            for item in items:
                if item.get("column_values") and item["column_values"][0].get("text"):
                    existing_items_map[item["column_values"][0]["text"]] = {
                        "id": item["id"],
                        "name": item["name"],
                    }
                    item_count += 1

            log.info(
                f"  -> Fetched {len(items)} items on this page. Total fetched so far: {item_count}",
            )

            if not next_cursor:
                break

        except (KeyError, IndexError, TypeError, AttributeError) as e:
            log.error(
                f"  Could not parse existing items from Monday.com during fetch. Details: {e}. Stopping pagination.",
            )
            break

        time.sleep(0.5)

    log.info(
        f"  Found {len(existing_items_map)} existing items to compare against.",
    )

    # --- Handle Stale Entries ---
    # Find items on Monday that are NOT in the fresh portal_data and archive them.
    fresh_store_ids = {str(s.get("id")) for s in stores_data if s.get("id")}
    _handle_stale_entries(board_id, existing_items_map, fresh_store_ids)

    status_map = {1: "Inactive", 2: "Active"}
    display_status_map = {1: "Closed", 2: "Open", 3: "Busy"}

    # --- Stats for Discord Report ---
    stats = {
        "status": {"Active": 0, "Inactive": 0, "Other": 0},
        "display_status": {"Open": 0, "Busy": 0, "Closed": 0, "Other": 0},
        "fo_status_anomaly": 0,
    }

    for i, store in enumerate(stores_data):
        # This loop now only focuses on creating/updating items present in the fresh data
        log.info(f"  Processing store {i+1}/{len(stores_data)}: {store.get('name')}")
        store_id = str(store.get("id", ""))
        if not store_id:
            log.warning("  Skipping store with no ID.")
            continue
        item_name = store.get("name", "Unnamed Store")

        column_values = {"text_mkwdb7a": store.get("store_address", "")}

        # Process and count Outlet Status
        outlet_status_val = store.get("status")
        outlet_status_label = status_map.get(outlet_status_val)
        if outlet_status_label:
            column_values["color_mkvztyew"] = {"label": outlet_status_label}
            stats["status"][outlet_status_label] += 1
        else:
            stats["status"]["Other"] += 1

        # Process and count OFD Status
        display_status_val = store.get("display_status")
        display_status_label = display_status_map.get(display_status_val)
        if display_status_label:
            column_values["color_mkwdb5mh"] = {"label": display_status_label}
            stats["display_status"][display_status_label] += 1
        else:
            stats["display_status"]["Other"] += 1

        # --- NEW: Check for 'Busy' status anomaly ---
        if _check_busy_status_against_schedule(store):
            # If the store is busy but should be open, set the 'FO Status' column.
            # NOTE: Ensure the label "Yes" exists for this column on your board.
            column_values["color_mkxmcv9x"] = {"label": "Yes"}
            stats["fo_status_anomaly"] += 1
        else:
            # If the anomaly is not present, explicitly clear the 'FO Status' column.
            column_values["color_mkxmcv9x"] = None

        # --- End of Stat Counting ---

        mutation = None
        variables = {}

        if store_id in existing_items_map:
            monday_item_id = int(existing_items_map[store_id]["id"])
            log.info(f"     -> Updating existing item (ID: {monday_item_id})")
            column_values["name"] = item_name  # Add item name for update

            mutation = "mutation ($itemId: ID!, $boardId: ID!, $colVals: JSON!) { change_multiple_column_values (item_id: $itemId, board_id: $boardId, column_values: $colVals) { id } }"
            variables = {
                "itemId": monday_item_id,
                "boardId": board_id,
                "colVals": json.dumps(column_values),
            }

        else:
            log.info(f"    -> Creating new item for Store ID: {store_id}")
            create_column_values = column_values.copy()
            create_column_values[store_id_column] = store_id

            mutation = "mutation ($boardId: ID!, $groupId: String!, $itemName: String!, $colVals: JSON!) { create_item (board_id: $boardId, group_id: $groupId, item_name: $itemName, column_values: $colVals) { id } }"

            variables = {
                "boardId": board_id,
                "groupId": group_id,
                "itemName": item_name,
                "colVals": json.dumps(create_column_values),
            }

        if mutation:
            result = execute_monday_query(mutation, variables)
            if not result:
                log.error(
                    f"  Failed to upload item for Store ID {store_id}. Aborting process for this merchant.",
                )
                return
        time.sleep(0.3)
    board_name = get_board_name(board_id)
    log.info(f"✅ Monday.com board update complete for this merchant.")

    # --- Send Discord Notification ---
    summary_message = (
        f"**Objective:** Count total outlets per portal and label their status.\n"
        f"**Channel:** ShopeeFood\n"
        f"**Portal:** `{portal_name}`\n"
        f"**Total Tasks:** `{len(stores_data)}`"
    )

    fields = [
        {
            "name": "Outlet Status",
            "value": f"🟢 Active: `{stats['status']['Active']}`\n"
            f"🔴 Inactive: `{stats['status']['Inactive']}`",
            "inline": True,
        },
        {
            "name": "OFD Status",
            "value": f"🟢 Open: `{stats['display_status']['Open']}`\n"
            f"🟡 Busy: `{stats['display_status']['Busy']}`\n"
            f"🔴 Closed: `{stats['display_status']['Closed']}`",
            "inline": True,
        },
        {
            "name": "ForceOpen Status",
            "value": f"⚠️ Flagged as 'Yes': `{stats['fo_status_anomaly']}`",
            "inline": False,
        },
    ]

    send_discord_notification(
        DISCORD_WEBHOOK_URL, f"📊 {board_name} Report", summary_message, fields=fields
    )


def get_latest_raw_file(merchant_name):
    """
    Finds the latest raw JSON file for a given merchant in the 'raw_data' directory.
    """
    raw_dir = "raw_data"
    if not os.path.exists(raw_dir):
        log.error(f"Raw data directory '{raw_dir}' not found.")
        return None

    safe_merchant_name = re.sub(r'[\\/*?:"<>|]', "", merchant_name).replace(" ", "_")
    # Matches format: raw_stores_{MerchantName}_{Timestamp}.json
    pattern = os.path.join(raw_dir, f"shopeefood_{safe_merchant_name}_*.json")

    files = glob.glob(pattern)
    if not files:
        return None

    # Sort by filename (which includes timestamp YYYYMMDD_HHMMSS) descending
    files.sort(reverse=True)
    return files[0]


def run_store_details_sync(browser_session, merchant_task):
    """
    The core logic for syncing store details for a single merchant.
    This function is called by the main_runner.
    """
    group_id = GROUP_MAPPING.get(merchant_task["output_name"])
    if not group_id:
        log.error(
            f"No Group ID found in settings.py for '{merchant_task['output_name']}'. Skipping."
        )
        return

    # --- NEW LOGIC: Load from Raw JSON instead of scraping ---
    merchant_name = merchant_task["output_name"]
    latest_file = get_latest_raw_file(merchant_name)

    if not latest_file:
        log.error(
            f"No raw data file found for '{merchant_name}'. Please run the extraction task first."
        )
        return

    log.info(f"Loading raw data from: {latest_file}")
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            raw_stores = json.load(f)
    except Exception as e:
        log.error(f"Failed to load JSON file: {e}")
        return

    if raw_stores:
        # Deduplication logic (moved from collect_shopee_data)
        raw_count = len(raw_stores)
        final_df = pd.DataFrame(raw_stores).drop_duplicates(subset=["id"], keep="first")
        clean_count = len(final_df)
        duplicates_removed = raw_count - clean_count
        log.info(f"  Removed {duplicates_removed} duplicate entries.")
        log.info(f"✅ Prepared {clean_count} unique stores for upload.")

        portal_data = final_df.to_dict("records")

        upload_to_monday(
            MONDAY_BOARD_ID,
            group_id,
            portal_data,
            merchant_name,
        )
    else:
        log.warning(f"Raw data file '{latest_file}' was empty.")
