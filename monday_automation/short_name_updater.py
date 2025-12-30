import os
import json
import logging
import time
from dotenv import load_dotenv
import requests
import sys

# --- Setup Project Path ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# It's better to use the common GraphQL executor for consistency and better error handling
from common.monday_api import execute_monday_query


# --- Configuration ---

# Load environment variables (stores your API key)
load_dotenv()
API_KEY = os.getenv("MONDAY_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
BATCH_SIZE = 25  # Number of items to update in a single bulk mutation
if not API_KEY:
    raise ValueError(
        "MONDAY_API_KEY not found in .env file. Please create a .env file and add it."
    )

# --- Board and Column IDs ---

SOURCE_BOARD_ID = 5006292952
TARGET_BOARD_ID = 2075483964
TARGET_GROUP_ID = "group_mkvxp4cr"

# Source column IDs
SOURCE_KEY_COL = "text_mkvc896g"  # 'Store ID'
SOURCE_VAL_COL = "text_mkwdygde"  # 'Short Name'

SYNC_MAP = [
    {
        "name": "F1",
        "source_group": "group_mkw46q72",
        "target_sid": "text_mktz8s96",  # F - S SID
        "target_name": "text_mkvwebs8",  # F - S Short Name
    },
    {
        "name": "W1",
        "source_group": "group_mks93rx3",
        "target_sid": "text_mkvwqq8c",  # W - S SID
        "target_name": "text_mkvwwe3d",  # W - S Short Name
    },
    {
        "name": "L1",
        "source_group": "group_mkw4rjmz",
        "target_sid": "text_mkvw90wc",  # L - S SID
        "target_name": "text_mkvw9kd0",  # L - S Short Name
    },
    {
        "name": "DE1",
        "source_group": "group_mkw45f1v",
        "target_sid": "text_mkvwzjaa",  # DE - S SID
        "target_name": "text_mkvw6xae",  # DE - S Short Name
    },
]

# --- Helper Functions ---


def send_discord_notification(webhook_url, message):
    """Sends a notification message to a Discord webhook."""
    if not webhook_url:
        logging.info("Discord webhook URL not configured. Skipping notification.")
        return

    # For better formatting in Discord, use an embed
    payload = {
        "embeds": [
            {
                "title": "Monday.com Automation Report",
                "description": message,
                "color": 3066993,
            }
        ]  # Green color
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logging.info("Successfully sent Discord notification.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send Discord notification: {e}")


def get_all_items_graphql(board_id, group_id):
    """Fetches all items from a single group on a board, handling pagination."""
    all_items = []
    cursor = None
    query = """
    query getItems($boardId: [ID!]!, $groupIds: [String!], $cursor: String) { # Using groupIds for compatibility with single/multiple
        boards(ids: $boardId) {
            groups(ids: $groupIds) {
                items_page(limit: 500, cursor: $cursor) {
                    cursor
                    items { id name group { id } column_values { id text } }
                }
            }
        }
    }
    """
    while True:
        try:
            # Always pass group_id as a list
            variables = {
                "boardId": [board_id],
                "groupIds": [group_id],
                "cursor": cursor,
            }

            response = execute_monday_query(query, variables)

            if not response or "errors" in response:
                logging.error(
                    f"Error fetching items for board {board_id}: {response.get('errors')}"
                )
                break

            # The response structure is now nested inside 'groups'
            groups_data = response["data"]["boards"][0].get("groups", [])
            if not groups_data:
                logging.warning(
                    f"Group ID {group_id} not found on board '{board_id}' or is empty. No items fetched."
                )
                break

            items_page = groups_data[0].get("items_page", {})
            items = items_page.get("items", [])
            all_items.extend(items)

            cursor = items_page.get("cursor")
            if not cursor:
                break
            time.sleep(0.5)  # Be respectful of API rate limits

        except Exception as e:
            logging.error(
                f"Exception while fetching items for board {board_id}: {e}",
                exc_info=True,
            )
            break
    return all_items


def get_col_value(item, column_id):
    """Safely gets the 'text' value from an item's column_values."""
    # Using a generator expression and next is slightly more efficient
    return next(
        (
            col.get("text")
            for col in item.get("column_values", [])
            if col.get("id") == column_id
        ),
        None,
    )


def build_lookup_map(items_in_group, key_col, val_col):
    """Builds a {key: value} map for a specific group from a list of items."""
    lookup_map = {}
    for item in items_in_group:
        key = get_col_value(item, key_col)
        val = get_col_value(item, val_col)
        if key and val:
            if key in lookup_map:
                logging.warning(
                    f"Duplicate Store ID '{key}' found in group {item.get('group', {}).get('id')}."
                )
            lookup_map[key] = val
    return lookup_map


# --- Main Sync Logic ---


def main():
    """Main script execution."""
    logging.info("Starting short name sync script...")

    # --- Step 1: Build Lookup Maps from Source Board ---
    source_group_ids = [m["source_group"] for m in SYNC_MAP]
    logging.info(
        f"Fetching all items from SOURCE board ({SOURCE_BOARD_ID}) for groups: {source_group_ids}"
    )
    all_source_items = []
    try:
        # Fetch items group by group to handle pagination cursors correctly
        for group_id in source_group_ids:
            logging.info(f"  -> Fetching items for group: {group_id}")
            items_in_group = get_all_items_graphql(SOURCE_BOARD_ID, group_id)
            all_source_items.extend(items_in_group)
            logging.info(f"  -> Found {len(items_in_group)} items in this group.")

        logging.info(f"Found {len(all_source_items)} total items on source board.")
    except Exception as e:
        logging.critical(f"FATAL: Could not fetch source items. Error: {e}")
        return

    lookup_maps = {}
    for mapping in SYNC_MAP:
        group_id = mapping["source_group"]
        group_name = mapping["name"]
        logging.info(f"Building lookup map for group: {group_name} ({group_id})...")

        # Filter items for the current group
        items_for_group = [
            item
            for item in all_source_items
            if item.get("group", {}).get("id") == group_id
        ]

        lookup_map = build_lookup_map(items_for_group, SOURCE_KEY_COL, SOURCE_VAL_COL)
        lookup_maps[group_name] = lookup_map
        logging.info(f"  -> Built map with {len(lookup_map)} entries.")

    # --- Step 2: Process and Update Target Board ---

    logging.info(
        f"\nFetching all items from TARGET board ({TARGET_BOARD_ID}) in group {TARGET_GROUP_ID}..."
    )
    try:
        # Fetch only the items we care about
        target_items = get_all_items_graphql(TARGET_BOARD_ID, TARGET_GROUP_ID)
        logging.info(f"Found {len(target_items)} items to process in target group.")
    except Exception as e:
        print(f"FATAL: Could not fetch target items. Error: {e}")
        return

    total_updates_sent = 0
    items_updated_count = 0

    logging.info(f"\nProcessing {len(target_items)} target items...")
    for item in target_items:
        item_id = item["id"]
        item_name = item["name"]
        updates_to_make = {}

        # Check all 4 mappings for this single item
        for mapping in SYNC_MAP:
            group_name = mapping["name"]
            target_sid_col = mapping["target_sid"]
            target_name_col = mapping["target_name"]
            current_map = lookup_maps[
                group_name
            ]  # Get the correct map (F, W, L, or DE)

            # 1. Get the SID to match from the target item
            sid_to_match = get_col_value(item, target_sid_col)

            if sid_to_match in current_map:
                # 2. We found a match in the source map!
                new_short_name = current_map[sid_to_match]

                # 3. Check if an update is actually needed
                current_short_name = get_col_value(item, target_name_col)

                if new_short_name != current_short_name:
                    # 4. Add the update to our batch for this item
                    updates_to_make[target_name_col] = new_short_name

        # After checking all 4 mappings, send the update if any changes were found
        if updates_to_make:
            logging.info(
                f"  Queueing update for item '{item_name}' ({item_id}) with: {updates_to_make}"
            )
            try:
                mutation = """
                mutation ($itemId: ID!, $boardId: ID!, $columnValues: JSON!) {
                    change_multiple_column_values(item_id: $itemId, board_id: $boardId, column_values: $columnValues) {
                        id
                    }
                }
                """
                variables = {
                    "itemId": item_id,
                    "boardId": TARGET_BOARD_ID,
                    "columnValues": json.dumps(updates_to_make),
                }

                result = execute_monday_query(mutation, variables)
                if not result or "errors" in result:
                    logging.error(
                        f"    !! ERROR updating item {item_id}: {result.get('errors')}"
                    )
                    continue

                total_updates_sent += len(updates_to_make)
                items_updated_count += 1

                # Be respectful of API rate limits
                time.sleep(0.2)

            except Exception as e:
                logging.error(
                    f"    !! EXCEPTION updating item {item_id}: {e}", exc_info=True
                )
    logging.info("\n--- Sync Complete ---")
    logging.info(f"Items Updated: {items_updated_count}")
    logging.info(f"Total Column Updates Sent: {total_updates_sent}")
    summary_message = f"**Sync Completed for short name**\n"

    logging.info("\n" + summary_message.replace("**", "").replace("`", ""))
    send_discord_notification(DISCORD_WEBHOOK_URL, summary_message)


if __name__ == "__main__":
    main()
