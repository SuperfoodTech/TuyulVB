import os
import time
import json
import logging
from dotenv import load_dotenv
import pandas as pd
from tqdm import tqdm
from common.monday_api import execute_monday_query

# --- CONFIGURATION ---
load_dotenv()
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
BOARD_ID = 2075483964
GROUP_ID = "group_mkvxp4cr"
EXCEL_FILE_PATH = "S1 Database Mitra - Cluster 1 FWL+D.xlsx"
EXCEL_MATCH_COLUMN = "Nama Outlet Asli Merchant"
EXCEL_PHONE_COLUMN = "No. Telp Pemilik"
WA_NUMBER_COLUMN_NAME = "WA Number"
COUNTRY_CODE = "ID"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_board_data(board_id, group_id):
    """Fetches all columns and items from the specified group."""
    logging.info(f"Fetching board structure and all items for board '{board_id}'...")
    column_map, item_map = {}, {}

    query_cols = f"query {{ boards(ids: {board_id}) {{ columns {{ id title }} }} }}"
    col_data = execute_monday_query(query_cols)
    if not col_data or "errors" in col_data:
        logging.error(f"Could not fetch board columns: {col_data.get('errors')}")
        return None, None
    for col in col_data["data"]["boards"][0]["columns"]:
        column_map[col["title"]] = col["id"]

    cursor = None
    while True:
        query_items = """
        query($boardId: ID!, $groupId: String, $cursor: String) {
            boards(ids: [$boardId]) {
                groups(ids: [$groupId]) {
                    items_page(limit: 500, cursor: $cursor) {
                        cursor
                        items { id name }
                    }
                }
            }
        }
        """
        variables = {"boardId": board_id, "groupId": group_id, "cursor": cursor}
        item_data = execute_monday_query(query_items, variables)

        if not item_data or "errors" in item_data:
            logging.error(f"Could not fetch items: {item_data.get('errors')}")
            break

        page_info = item_data["data"]["boards"][0]["groups"][0]["items_page"]
        for item in page_info["items"]:
            name_key = item["name"].strip().lower()
            if name_key in item_map:
                logging.warning(f"Duplicate item name found: '{item['name']}'")
            item_map[name_key] = item["id"]

        cursor = page_info.get("cursor")
        if not cursor:
            break

    logging.info(
        f"Found {len(column_map)} columns and {len(item_map)} unique item names."
    )
    return column_map, item_map


def update_single_item(board_id, column_id, item_id, phone_number):
    """Updates a single item using the reliable 'change_column_value' mutation."""
    mutation = """
    mutation ($itemId: ID!, $boardId: ID!, $columnId: String!, $value: JSON!) {
        change_column_value(
            item_id: $itemId,
            board_id: $boardId,
            column_id: $columnId,
            value: $value
        ) {
            id
        }
    }
    """
    clean_phone = str(phone_number).strip().split(".")[0]
    phone_value_obj = {"phone": clean_phone, "countryShortName": COUNTRY_CODE}
    variables = {
        "itemId": int(item_id),
        "boardId": board_id,
        "columnId": column_id,
        "value": json.dumps(phone_value_obj),
    }

    result = execute_monday_query(mutation, variables)
    if not result or "errors" in result:
        logging.error(f"Failed to update item {item_id}. Error: {result.get('errors')}")
        return False
    return True


def main():
    if not MONDAY_API_KEY:
        logging.critical("MONDAY_API_KEY not found. Exiting.")
        return

    column_map, item_map = get_board_data(BOARD_ID, GROUP_ID)
    if column_map is None or item_map is None:
        logging.critical("Failed to fetch initial board data. Aborting.")
        return

    target_column_id = column_map.get(WA_NUMBER_COLUMN_NAME)
    if not target_column_id:
        logging.critical(f"Column '{WA_NUMBER_COLUMN_NAME}' not found. Aborting.")
        return
    logging.info(
        f"Found target column '{WA_NUMBER_COLUMN_NAME}' with ID: {target_column_id}"
    )

    try:
        df = pd.read_excel(EXCEL_FILE_PATH)
        logging.info(f"Successfully loaded Excel file: {EXCEL_FILE_PATH}")
    except FileNotFoundError:
        logging.critical(f"Excel file not found at '{EXCEL_FILE_PATH}'. Aborting.")
        return

    logging.info("Matching Excel data to Monday.com items (case-insensitive)...")
    update_pairs = []
    unmatched_outlets = []

    for _, row in df.iterrows():
        outlet_name_key = str(row.get(EXCEL_MATCH_COLUMN, "")).strip().lower()
        phone_number = row.get(EXCEL_PHONE_COLUMN)

        if not outlet_name_key or pd.isna(phone_number):
            continue

        item_id = item_map.get(outlet_name_key)
        if item_id and str(item_id).isdigit():
            update_pairs.append((item_id, phone_number))
        else:
            unmatched_outlets.append(str(row.get(EXCEL_MATCH_COLUMN, "")))

    logging.info(
        f"Matched: {len(update_pairs)} items. Unmatched: {len(unmatched_outlets)} items."
    )
    if unmatched_outlets:
        logging.warning(
            f"--- Unmatched Outlet Names ---\n  - " + "\n  - ".join(unmatched_outlets)
        )

    if not update_pairs:
        logging.info("No items were matched. Nothing to update.")
        return

    logging.info(f"Preparing to update {len(update_pairs)} items one by one...")

    success_count = 0
    # Use tqdm to create a progress bar for the item-by-item updates
    for item_id, phone_number in tqdm(update_pairs, desc="Updating Items"):
        if update_single_item(BOARD_ID, target_column_id, item_id, phone_number):
            success_count += 1
        time.sleep(1)  # Add a delay to be respectful of the API rate limit

    logging.info(
        f"Script finished. Successfully updated {success_count}/{len(update_pairs)} items."
    )


if __name__ == "__main__":
    main()
