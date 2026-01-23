import os
import sys
import json
import glob
import time
import re
from datetime import datetime
from dotenv import load_dotenv

# --- Setup Project Path ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load environment variables
env_path = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path=env_path)

from common.monday_api import execute_monday_query
from common.logger import get_logger

log = get_logger("klikit_grab_val")

# --- Configuration ---
BOARD_ID = 5025182611
GROUP_ID = "group_mkys1dmf"
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "grab")

# Mapping configuration based on the prompt
ACCOUNT_CONFIG = {
    "F2S": {
        "sid_col": "text_mky9b8z9",
        "addr_col": "text_mkyp1rk7",
        "val_col": "color_mkysa9bq",
    },
    "W1": {
        "sid_col": "text_mky974s9",
        "addr_col": "text_mkyprm6z",
        "val_col": "color_mkysg3vv",
    },
    "L2": {
        "sid_col": "text_mky9pxvr",
        "addr_col": "text_mkypdqmg",
        "val_col": "color_mkysk744",
    },
    "DE1S": {
        "sid_col": "text_mky9z4ts",
        "addr_col": "text_mkyppp4n",
        "val_col": "color_mkysaz2e",
    },
}


def get_latest_json_for_account(account_name):
    """Finds the latest JSON file for the given account name."""
    # Pattern: grabfood_{account_name}_YYYYMMDD_HHMMSS.json
    # We check for the exact account name first
    pattern = os.path.join(RAW_DATA_DIR, f"grabfood_{account_name}_*.json")
    files = glob.glob(pattern)

    if not files:
        return None

    # Sort by modification time, latest first
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def load_grab_data(filepath):
    """Loads merchant data from JSON and returns a dict {merchantID: {address: ...}}."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Data is expected to be a list of merchants
            if isinstance(data, list):
                return {
                    str(m.get("merchantID")): m for m in data if m.get("merchantID")
                }
            else:
                log.error(
                    f"JSON content in {os.path.basename(filepath)} is not a list."
                )
                return {}
    except Exception as e:
        log.error(f"Failed to load {filepath}: {e}")
        return {}


def fetch_monday_items(board_id, group_id, column_ids):
    """Fetches items from Monday.com."""
    items = []
    cursor = None

    while True:
        query = """
            query ($boardId: [ID!], $groupId: [String!], $cursor: String, $colIds: [String!]) {
                boards (ids: $boardId) {
                    groups (ids: $groupId) {
                        items_page (limit: 500, cursor: $cursor) {
                            cursor
                            items {
                                id
                                name
                                column_values (ids: $colIds) {
                                    id
                                    text
                                }
                            }
                        }
                    }
                }
            }
        """
        variables = {
            "boardId": [board_id],
            "groupId": [group_id],
            "cursor": cursor,
            "colIds": column_ids,
        }

        response = execute_monday_query(query, variables)
        if not response or "errors" in response:
            log.error(f"Error fetching Monday items: {response}")
            break

        try:
            group_data = response["data"]["boards"][0]["groups"][0]
            items_page = group_data["items_page"]
            items.extend(items_page["items"])
            cursor = items_page["cursor"]
            if not cursor:
                break
        except (KeyError, IndexError, TypeError) as e:
            log.error(f"Error parsing Monday response: {e}")
            break

    return items


def validate_address_logic(item_name, address):
    """
    Validates if the address contains the item name.
    Handles case-insensitivity and hyphens by normalizing to alphanumeric only.
    """
    if not address or not item_name:
        return "Invalid"

    # Normalize: remove all non-alphanumeric characters and lowercase
    # This handles " - ", "-", " ", etc. effectively ignoring them for comparison
    name_clean = re.sub(r"[^a-z0-9]", "", item_name.lower())
    addr_clean = re.sub(r"[^a-z0-9]", "", address.lower())

    if name_clean in addr_clean:
        return "Valid"

    return "Invalid"


def process_batch_updates(board_id, updates):
    """Executes updates in batches."""
    BATCH_SIZE = 30
    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i : i + BATCH_SIZE]
        mutation_parts = []
        variables = {"boardId": int(board_id)}

        for idx, update in enumerate(batch):
            item_id_var = f"itemId_{idx}"
            col_vals_var = f"colVals_{idx}"
            variables[item_id_var] = update["itemId"]
            variables[col_vals_var] = json.dumps(update["colVals"])
            mutation_parts.append(
                f"update_{idx}: change_multiple_column_values (board_id: $boardId, item_id: ${item_id_var}, column_values: ${col_vals_var}) {{ id }}"
            )

        query = f"mutation ($boardId: ID!, {', '.join([f'$itemId_{j}: ID!, $colVals_{j}: JSON!' for j in range(len(batch))])}) {{ {' '.join(mutation_parts)} }}"
        execute_monday_query(query, variables)
        time.sleep(1)


def main():
    log.info("Starting Klikit Address Validation Script...")

    # 1. Fetch Monday Data
    all_sid_cols = [cfg["sid_col"] for cfg in ACCOUNT_CONFIG.values()]
    log.info(f"Fetching items from Board {BOARD_ID}, Group {GROUP_ID}...")
    monday_items = fetch_monday_items(BOARD_ID, GROUP_ID, all_sid_cols)
    log.info(f"Fetched {len(monday_items)} items.")

    if not monday_items:
        return

    # 2. Process each account
    for account_name, config in ACCOUNT_CONFIG.items():
        log.info(f"--- Processing Account: {account_name} ---")
        json_file = get_latest_json_for_account(account_name)

        if not json_file:
            log.warning(f"No JSON file found for {account_name}. Skipping.")
            continue

        log.info(f"Using data file: {os.path.basename(json_file)}")
        grab_data = load_grab_data(json_file)
        updates = []

        for item in monday_items:
            # Find the SID for this specific account in the item
            item_sid = next(
                (
                    cv["text"]
                    for cv in item.get("column_values", [])
                    if cv["id"] == config["sid_col"]
                ),
                None,
            )

            if item_sid and item_sid in grab_data:
                merchant_info = grab_data[item_sid]
                raw_address = merchant_info.get("address", "")
                status = validate_address_logic(item["name"], raw_address)

                updates.append(
                    {
                        "itemId": int(item["id"]),
                        "colVals": {
                            config["addr_col"]: raw_address,
                            config["val_col"]: {"label": status},
                        },
                    }
                )

        if updates:
            log.info(f"Applying {len(updates)} updates for {account_name}...")
            process_batch_updates(BOARD_ID, updates)
        else:
            log.info(f"No matches found for {account_name}.")


if __name__ == "__main__":
    main()
