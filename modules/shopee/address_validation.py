import time
import json
import os
from dotenv import load_dotenv
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.addressettings import (
    SOURCE_BOARD_ID,
    TARGET_BOARD_ID,
    MATCH_BOARD_ID,
    GROUP_MAPPING,
    TARGET_COL_STORE_ID,
    TARGET_COL_ADDRESS_STATUS,
    TARGET_COL_ADDRESS,
    MATCH_COL_STORE_ID,
    MATCH_COL_ADDRESS,
)

load_dotenv()
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
from common.monday_api import execute_monday_query
from common.notifications import send_discord_notification
from common.logger import get_logger

log = get_logger("shopee_address_validation")


def get_column_value(item, column_id):
    for col in item.get("column_values", []):
        if col.get("id") == column_id:
            return col.get("text", "")
    return ""


def fetch_all_items_from_board(board_id, group_id=None, columns=None):
    all_items = []
    cursor = None
    while True:
        if group_id:
            query = """
                query ($boardId: [ID!], $limit: Int, $cursor: String, $groupId: [String!]) {
                    boards(ids: $boardId) {
                        groups(ids: $groupId) {
                            items_page(limit: $limit, cursor: $cursor) {
                                cursor
                                items { id name column_values(ids: $columns) { id text } }
                            }
                        }
                    }
                }
            """
            variables = {
                "boardId": [board_id],
                "limit": 500,
                "cursor": cursor,
                "groupId": [group_id],
                "columns": columns or [],
            }
        else:
            query = """
                query ($boardId: [ID!], $limit: Int, $cursor: String) {
                    boards(ids: $boardId) {
                        items_page(limit: $limit, cursor: $cursor) {
                            cursor
                            items { id name column_values(ids: $columns) { id text } }
                        }
                    }
                }
            """
            variables = {
                "boardId": [board_id],
                "limit": 500,
                "cursor": cursor,
                "columns": columns or [],
            }

        response = execute_monday_query(query=query, variables=variables)

        if not response or not response.get("data", {}).get("boards"):
            log.error(f"Could not fetch items from board {board_id}.")
            return []
        board_data = response["data"]["boards"][0]

        if group_id:
            groups = board_data.get("groups", [])
            if not groups:
                log.warning(
                    f"Group '{group_id}' not found or is empty on board {board_id}."
                )
                break
            items_page = groups[0].get("items_page", {})
        else:
            items_page = board_data.get("items_page", {})

        items = items_page.get("items", [])
        all_items.extend(items)

        cursor = items_page.get("cursor")
        if not cursor:
            break
    return all_items


def build_match_item_map(items, store_id_col, address_col):
    """Builds a dictionary mapping store IDs to their addresses."""
    item_map = {}
    for item in items:
        store_id = get_column_value(item, store_id_col)
        if store_id:
            item_map[store_id] = {
                "address": get_column_value(item, address_col),
                "name": item.get("name"),
                "id": item.get("id"),
            }
    return item_map


def run_address_validation():
    """
    Main function to process outlets, validate addresses, and create new items.
    """
    status_labels = {
        "true": "True",
        "warning": "Warning",
        "false": "False",
    }
    stats = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
    MATCH_CACHE_FILE = "match_board_cache.json"

    if not MONDAY_API_KEY:
        log.error("MONDAY_API_KEY not found in environment variables. Exiting.")
        return

    # 1. Fetch all items from the source board
    log.info(f"Fetching all items from source board ID: {SOURCE_BOARD_ID}...")
    source_cols_to_fetch = list(GROUP_MAPPING.keys())
    source_items_data = fetch_all_items_from_board(
        SOURCE_BOARD_ID, columns=source_cols_to_fetch
    )
    total_items = len(source_items_data)

    if not source_items_data:
        log.info("No items found on the source board.")
        return
    log.info(f"Found {total_items} items to process from source board.")

    # 2. Fetch all existing items from target groups to prevent duplicates
    log.info("Fetching existing items from target board to prevent duplicates...")
    existing_target_items_map = {}
    for target_group_id, _ in GROUP_MAPPING.values():
        if target_group_id not in existing_target_items_map:
            log.info(f"Fetching existing items from target group: {target_group_id}")
            items_in_group = fetch_all_items_from_board(
                TARGET_BOARD_ID,
                group_id=target_group_id,
                columns=[TARGET_COL_STORE_ID],
            )
            store_id_map = {
                get_column_value(item, TARGET_COL_STORE_ID): item["id"]
                for item in items_in_group
                if get_column_value(item, TARGET_COL_STORE_ID)
            }
            existing_target_items_map[target_group_id] = store_id_map

    # 3. Load matched items from local cache or fetch from API if cache doesn't exist
    match_items_map = {}
    if os.path.exists(MATCH_CACHE_FILE):
        log.info(
            f"Loading matched items from local cache: '{MATCH_CACHE_FILE}'. To refresh, delete this file."
        )
        with open(MATCH_CACHE_FILE, "r") as f:
            match_items_map = json.load(f)
    else:
        log.info(
            "No local cache found. Fetching all matched items from API to build cache..."
        )
        for _, (_, match_group_id) in GROUP_MAPPING.items():
            if match_group_id not in match_items_map:
                log.info(
                    f"Fetching items from match group '{match_group_id}' on board {MATCH_BOARD_ID}."
                )
                match_items = fetch_all_items_from_board(
                    MATCH_BOARD_ID,
                    group_id=match_group_id,
                    columns=[
                        MATCH_COL_STORE_ID,
                        MATCH_COL_ADDRESS,
                    ],
                )
                match_items_map[match_group_id] = build_match_item_map(
                    items,
                    MATCH_COL_STORE_ID,
                    MATCH_COL_ADDRESS,
                )
        log.info(
            f"Saving matched items to local cache: '{MATCH_CACHE_FILE}' for future runs."
        )
        with open(MATCH_CACHE_FILE, "w") as f:
            json.dump(match_items_map, f, indent=2)

    for i, item in enumerate(source_items_data):
        outlet_name = item.get("name", "Unnamed Outlet")
        log.info(f"--- [{i+1}/{total_items}] Processing Outlet: {outlet_name} ---")

        for source_col_id, (
            target_group_id,
            match_group_id,
        ) in GROUP_MAPPING.items():
            store_id = get_column_value(item, source_col_id)

            if not store_id:
                log.warning(
                    f"  -> Store ID is empty for '{outlet_name}' in column '{source_col_id}'. Proceeding to write entry with empty Store ID."
                )
            else:
                log.info(f"  -> Processing Store ID '{store_id}'...")

            address_status = "false"
            address_to_write = ""

            group_match_map = match_items_map.get(match_group_id, {})
            match_data = group_match_map.get(store_id)

            if store_id:  # Only attempt to match if store_id exists
                if match_data:
                    matched_address = match_data.get("address", "")
                    log.info(
                        f"  -> Found matching Store ID '{store_id}' in group '{match_group_id}'."
                    )

                    if (
                        matched_address
                        and outlet_name.lower() in matched_address.lower()
                    ):
                        address_status = "true"
                        log.info(
                            "  -> Validation SUCCESS: Address contains outlet name."
                        )
                    else:
                        address_status = "warning"
                        address_to_write = matched_address
                        log.warning(
                            f"  -> Validation WARNING: Address does not contain outlet name. Address: '{matched_address}'"
                        )
                else:
                    log.error(
                        f"  -> Validation FAILED: No matching Store ID '{store_id}' found in group '{match_group_id}'."
                    )

            column_values_dict = {
                TARGET_COL_ADDRESS_STATUS: {
                    "label": status_labels.get(address_status, "False")
                },
                TARGET_COL_ADDRESS: address_to_write,
            }

            existing_item_id = (
                existing_target_items_map.get(target_group_id, {}).get(store_id)
                if store_id
                else None
            )

            if existing_item_id:
                log.info(
                    f"  -> Store ID '{store_id}' already exists. Updating item ID: {existing_item_id}."
                )
                update_query = """
                    mutation ($itemId: ID!, $boardId: ID!, $colVals: JSON!) {
                        change_multiple_column_values (item_id: $itemId, board_id: $boardId, column_values: $colVals) {
                            id
                        }
                    }
                """
                update_vars = {
                    "itemId": existing_item_id,
                    "boardId": TARGET_BOARD_ID,
                    "colVals": json.dumps(column_values_dict),
                }
                update_response = execute_monday_query(
                    query=update_query, variables=update_vars
                )
                if update_response:
                    log.info(f"  -> Successfully updated item {existing_item_id}.")
                    stats["updated"] += 1
                else:
                    log.error(f"  -> Failed to update item for '{outlet_name}'.")
                    stats["failed"] += 1

            else:
                log.info(
                    f"  -> Creating new item on target board '{TARGET_BOARD_ID}' in group '{target_group_id}'..."
                )
                # Only add store_id on creation
                column_values_dict[TARGET_COL_STORE_ID] = store_id
                create_query = """
                    mutation ($boardId: ID!, $groupId: String!, $itemName: String!, $colVals: JSON!) {
                        create_item (board_id: $boardId, group_id: $groupId, item_name: $itemName, column_values: $colVals) {
                            id
                        }
                    }
                """
                create_vars = {
                    "boardId": TARGET_BOARD_ID,
                    "groupId": target_group_id,
                    "itemName": outlet_name,
                    "colVals": json.dumps(column_values_dict),
                }
                create_response = execute_monday_query(
                    query=create_query, variables=create_vars
                )
                if create_response and create_response.get("data", {}).get(
                    "create_item"
                ):
                    new_item_id = create_response["data"]["create_item"]["id"]
                    log.info(f"  -> Successfully created item with ID: {new_item_id}")
                    stats["created"] += 1
                    # Add to local map to prevent re-creation in the same run
                    existing_target_items_map.setdefault(target_group_id, {})[
                        store_id
                    ] = new_item_id
                else:
                    log.error(f"  -> Failed to create item for '{outlet_name}'.")
                    stats["failed"] += 1

    log.info("--- Script finished ---")
    summary_message = (
        f"Processed {total_items} source outlets.\n"
        f"**Created**: {stats['created']}\n"
        f"**Updated**: {stats['updated']}\n"
        f"**Failed**: {stats['failed']}"
    )
    log.info(summary_message)

    # Send Discord notification
    send_discord_notification(
        DISCORD_WEBHOOK_URL,
        "Shopee Address Validation Report",
        summary_message,
        color=5814783,  # Blue
    )


if __name__ == "__main__":
    run_address_validation()
