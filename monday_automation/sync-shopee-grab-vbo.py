import os
import json
import logging
import time
from dotenv import load_dotenv
import requests
import argparse
import sys

# --- Setup Project Path ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.monday_api import execute_monday_query
from common.notifications import send_discord_notification

# --- Configuration ---
load_dotenv()
API_KEY = os.getenv("MONDAY_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

if not API_KEY:
    raise ValueError(
        "MONDAY_API_KEY not found in .env file. Please create a .env file and add it."
    )


CONFIG_FILE_PATH = os.path.join(
    os.path.dirname(__file__), "config", "vbo_sync_config.json"
)


def load_sync_map(file_path):
    """Loads the sync map configuration from a JSON file."""
    try:
        with open(file_path, "r") as f:
            logging.info(f"Loading sync configuration from {file_path}")
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Configuration file not found at {file_path}. Aborting.")
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in configuration file {file_path}. Aborting.")
        sys.exit(1)


# --- Helper Functions ---

def get_all_items_from_group(board_id, group_id, column_ids):
    """Fetches all items from a single group on a board, handling pagination."""
    all_items = []
    cursor = None
    query = """
    query getItems($boardId: [ID!]!, $groupIds: [String!], $cursor: String, $columnIds: [String!]) {
        boards(ids: $boardId) {
            groups(ids: $groupIds) {
                items_page(limit: 500, cursor: $cursor) {
                    cursor
                    items { id name column_values(ids: $columnIds) { id text } }
                }
            }
        }
    }
    """
    while True:
        variables = {
            "boardId": [board_id],
            "groupIds": [group_id],
            "cursor": cursor,
            "columnIds": column_ids,
        }
        response = execute_monday_query(query, variables)
        if not response or "errors" in response:
            logging.error(
                f"Error fetching items for board {board_id}, group {group_id}: {response.get('errors')}"
            )
            break
        groups_data = response["data"]["boards"][0].get("groups", [])
        if not groups_data:
            logging.warning(
                f"Group ID {group_id} not found on board '{board_id}' or is empty."
            )
            break
        items_page = groups_data[0].get("items_page", {})
        items = items_page.get("items", [])
        all_items.extend(items)
        cursor = items_page.get("cursor")
        if not cursor:
            break
        time.sleep(0.5)
    return all_items


def get_col_value(item, column_id):
    """Safely gets the 'text' value from an item's column_values."""
    return next(
        (
            col.get("text")
            for col in item.get("column_values", [])
            if col.get("id") == column_id
        ),
        None,
    )


def build_lookup_map(items, key_col, val_cols):
    """Builds a {key: {val1: ..., val2: ...}} map from a list of items."""
    lookup_map = {}
    for item in items:
        key = get_col_value(item, key_col)
        if key:
            if key in lookup_map:
                logging.warning(f"Duplicate Store ID '{key}' found in source data.")

            lookup_map[key] = {
                val_col: get_col_value(item, val_col) for val_col in val_cols
            }
            lookup_map[key]["name"] = item.get("name")  # Always include the item name
    return lookup_map


# --- Main Sync Logic ---


def main(dry_run=False):
    """Main script execution."""
    # Load the configuration from the external file
    config = load_sync_map(CONFIG_FILE_PATH)
    TARGET_BOARD_ID = config["target_board_id"]
    TARGET_GROUP_ID = config["target_group_id"]
    SYNC_MAP = config["sync_map"]

    if dry_run:
        logging.warning("=" * 50)
        logging.warning("### SCRIPT IS RUNNING IN DRY-RUN MODE ###")
        logging.warning("### NO ACTUAL UPDATES WILL BE SENT TO MONDAY.COM ###")
        logging.warning("=" * 50)
    else:
        logging.info("Starting full name and short name sync script...")

    stats = {
        "total_updates_queued": 0,
        "items_to_update": 0,
        "errors": 0,
        "items_updated_successfully": 0,
        "skipped_no_change": 0,
    }
    # --- Step 1: Build all lookup maps from all source boards/groups ---
    logging.info("--- Building Lookup Maps from Source Boards ---")
    lookup_maps = {}
    for mapping in SYNC_MAP:
        map_key = f"{mapping['source_board']}_{mapping['source_group']}"
        if map_key in lookup_maps:
            continue

        logging.info(
            f"Fetching source items for: {mapping['name']} (Board: {mapping['source_board']}, Group: {mapping['source_group']})"
        )

        cols_to_fetch = [mapping["source_sid_col"]]
        if mapping["type"] == "shopee":
            cols_to_fetch.append(mapping["source_short_name_col"])

        source_items = get_all_items_from_group(
            mapping["source_board"], mapping["source_group"], cols_to_fetch
        )

        val_cols_map = {"name": "name"}  # map internal name to monday name
        if mapping["type"] == "shopee":
            val_cols_map["short_name"] = mapping["source_short_name_col"]

        lookup_maps[map_key] = build_lookup_map(
            source_items, mapping["source_sid_col"], cols_to_fetch
        )
        logging.info(f"  -> Built map with {len(lookup_maps[map_key])} entries.")

    # --- Step 2: Fetch all target items ---
    logging.info(f"\n--- Fetching Target Items from Board {TARGET_BOARD_ID} ---")
    # Fetch all columns we need to read from the target board for comparison
    target_cols_to_fetch = set()
    for m in SYNC_MAP:
        target_cols_to_fetch.add(m["target_sid_col"])
        target_cols_to_fetch.add(m["target_full_name_col"])
        if "target_short_name_col" in m:
            target_cols_to_fetch.add(m["target_short_name_col"])

    target_items = get_all_items_from_group(
        TARGET_BOARD_ID, TARGET_GROUP_ID, list(target_cols_to_fetch)
    )
    logging.info(f"Found {len(target_items)} items to process in target group.")

    # --- Step 3: Process and update target items ---
    logging.info(f"\n--- Processing {len(target_items)} Target Items ---")
    for item in target_items:
        item_id = item["id"]
        item_name = item["name"]
        updates_to_make = {}

        for mapping in SYNC_MAP:
            sid_to_match = get_col_value(item, mapping["target_sid_col"])
            if not sid_to_match:
                continue

            map_key = f"{mapping['source_board']}_{mapping['source_group']}"
            source_data = lookup_maps.get(map_key, {}).get(sid_to_match)

            if source_data:
                # --- Check and update full name ---
                new_full_name = source_data.get("name", "")
                current_full_name = get_col_value(item, mapping["target_full_name_col"])
                if new_full_name != (current_full_name or ""):
                    updates_to_make[mapping["target_full_name_col"]] = new_full_name

                # --- Check and update short name (if applicable) ---
                if mapping["type"] == "shopee":
                    new_short_name = source_data.get(
                        mapping["source_short_name_col"], ""
                    )
                    current_short_name = get_col_value(
                        item, mapping["target_short_name_col"]
                    )
                    if new_short_name != (current_short_name or ""):
                        updates_to_make[mapping["target_short_name_col"]] = (
                            new_short_name
                        )

        if updates_to_make:
            log_prefix = "[DRY RUN] Would update" if dry_run else "Queueing update for"
            logging.info(f"  {log_prefix} item '{item_name}' ({item_id}).")
            stats["items_to_update"] += 1
            stats["total_updates_queued"] += len(updates_to_make)

            if not dry_run:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        mutation = """
                        mutation ($itemId: ID!, $boardId: ID!, $columnValues: JSON!) {
                            change_multiple_column_values(item_id: $itemId, board_id: $boardId, column_values: $columnValues) { id }
                        }
                        """
                        variables = {
                            "itemId": item_id,
                            "boardId": TARGET_BOARD_ID,
                            "columnValues": json.dumps(updates_to_make),
                        }
                        result = execute_monday_query(mutation, variables)

                        if (
                            not result
                            or "errors" in result
                            or "error_message" in result
                        ):
                            error_details = (
                                result.get("errors")
                                if result
                                else "API call failed, no response received."
                            )
                            raise Exception(f"API returned an error: {error_details}")

                        # If successful, break the retry loop
                        logging.info(
                            f"    -> Successfully updated item '{item_name}' ({item_id})."
                        )
                        stats["items_updated_successfully"] += 1
                        time.sleep(0.2)
                        break

                    except Exception as e:
                        logging.warning(
                            f"    !! Attempt {attempt + 1}/{max_retries} failed for item {item_id}: {e}"
                        )
                        if attempt < max_retries - 1:
                            delay = 2 ** (
                                attempt + 1
                            )  # Exponential backoff (2, 4 seconds)
                            logging.info(f"    -> Retrying in {delay} seconds...")
                            time.sleep(delay)
                        else:
                            logging.error(
                                f"    !! FAILED to update item {item_id} after {max_retries} attempts."
                            )
                            stats["errors"] += 1
                            # Add the failed item to a list for the final report
                            stats.setdefault("failed_items", []).append(
                                f"'{item_name}' ({item_id})"
                            )

        else:
            logging.info(
                f"  Skipping item '{item_name}' ({item_id}). No changes needed."
            )
            stats["skipped_no_change"] += 1

    logging.info("\n--- Sync Complete ---")
    report_title = (
        "**DRY RUN** Sync Report"
        if dry_run
        else "**Sync Completed for Full/Short Names**"
    )
    summary_message = (
        f"{report_title}\n\n"
        f"- **Items to Update:** `{stats['items_to_update']}`\n"
        f"- **Total Column Updates Queued:** `{stats['total_updates_queued']}`\n"
        f"- **Items Skipped (No Change):** `{stats['skipped_no_change']}`\n"
        f"- **Errors:** `{stats['errors']}`"
        f"- **Items Successfully Updated:** `{stats['items_updated_successfully']}`"
    )

    # Add list of failed items to the report if any
    if stats.get("failed_items"):
        failed_list = "\n".join(stats["failed_items"])
        summary_message += f"\n\n**Failed Items:**\n```{failed_list}```"

    logging.info(summary_message.replace("**", "").replace("`", ""))

    # Send the general report (for both dry-run and production)
    send_discord_notification(
        DISCORD_WEBHOOK_URL,
        title="VBO Database Sync Report",
        description=summary_message,
    )

    # --- NEW: Send a success-only notification if not a dry run ---
    if not dry_run and stats["items_updated_successfully"] > 0:
        success_desc = (
            f"✅ **Items Updated:** `{stats['items_updated_successfully']}`\n"
            f"⏭️ **Items Skipped (No Change):** `{stats['skipped_no_change']}`"
        )
        success_color = 3066993  # Green
        if stats["errors"] > 0:
            success_desc += f"\n\n⚠️ **Note:** `{stats['errors']}` items failed to update. Please check the full report for details."
            success_color = 15105570  # Orange

        send_discord_notification(
            DISCORD_WEBHOOK_URL, "VBO Database Sync Successful", success_desc, color=success_color
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync full and short names to a Monday.com board."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the script without making any actual changes to the board.",
    )
    args = parser.parse_args()

    main(dry_run=args.dry_run)
