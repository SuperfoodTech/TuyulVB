import sys
import os
import pandas as pd
import json
import logging

# --- PATH SETUP ---
# Add project root to path to allow importing from common
# This file is in modules/monday/automation/ -> 3 levels deep from root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

# --- IMPORTS ---
try:
    from common.monday_api import execute_monday_query
    from common.logger import get_logger
except ImportError as e:
    print(f"Error importing common modules: {e}")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1)

# --- LOGGING SETUP ---
logger = get_logger("input-wa")

BOARD_ID = 5026222269  # Target Board ID (Integer)
GROUP_ID = "topics"  # Target Group ID (String, e.g., 'topics', 'new_group_123')
COLUMN_ID = "numeric_mkzw11dt"  # The specific column ID to populate (e.g., 'text', 'status', 'numbers').


EXCEL_FILE_PATH = r"D:\Project\Intern Superfood - SQA\Experimental\sf-automation\Book1.xlsx"  # Full path to your Excel file
SHEET_NAME = 0

# ----------------------------------


def fetch_existing_items(board_id, group_id):
    """
    Fetches existing items from the specific board and group as a list (preserving order).
    Returns a list: [{"id": item_id, "name": item_name}, ...]
    """
    logger.info(f"Fetching existing items from Board {board_id}, Group {group_id}...")

    query = """
    query ($board_id: ID!, $group_id: [String]) {
        boards (ids: [$board_id]) {
            groups (ids: $group_id) {
                items_page (limit: 500) {
                    items {
                        id
                        name
                    }
                }
            }
        }
    }
    """

    variables = {"board_id": board_id, "group_id": [group_id]}

    response = execute_monday_query(query, variables)
    existing_items = []

    if response and "data" in response and "boards" in response["data"]:
        boards = response["data"]["boards"]
        if boards and len(boards) > 0:
            groups = boards[0].get("groups", [])
            for group in groups:
                items_page = group.get("items_page", {})
                items = items_page.get("items", [])
                for item in items:
                    existing_items.append({"id": item["id"], "name": item["name"]})

    logger.info(f"Found {len(existing_items)} existing items.")
    return existing_items


def create_monday_item(item_name, column_values=None):
    """
    Creates an item in Monday.com.
    """
    query = """
    mutation ($board_id: ID!, $group_id: String!, $item_name: String!, $column_values: JSON!) {
        create_item (board_id: $board_id, group_id: $group_id, item_name: $item_name, column_values: $column_values) {
            id
        }
    }
    """

    variables = {"board_id": BOARD_ID, "group_id": GROUP_ID, "item_name": item_name}

    if column_values:
        # The Monday API expects `column_values` as a JSON string in the
        # variables payload (quirk of the API). Match the repo pattern by
        # stringifying the dict here.
        variables["column_values"] = json.dumps(column_values)

    return execute_monday_query(query, variables)


def update_monday_item(item_id, column_values):
    """
    Updates column values for an existing item.
    """
    if not column_values:
        return None  # Nothing to update

    query = """
    mutation ($board_id: ID!, $item_id: ID!, $column_values: JSON!) {
        change_multiple_column_values (board_id: $board_id, item_id: $item_id, column_values: $column_values) {
            id
        }
    }
    """

    variables = {
        "board_id": BOARD_ID,
        "item_id": item_id,
        # The Monday API expects the `column_values` variable to be a JSON
        # string. Stringify to match other scripts in this repo.
        "column_values": json.dumps(column_values),
    }

    return execute_monday_query(query, variables)


def process_excel_upload():
    if "path" in EXCEL_FILE_PATH and "to" in EXCEL_FILE_PATH:
        logger.error(
            "Please configure the EXCEL_FILE_PATH variable in the script before running."
        )
        return

    if not os.path.exists(EXCEL_FILE_PATH):
        logger.error(f"Excel file not found at: {EXCEL_FILE_PATH}")
        return

    # 1. Fetch existing items first (List for ordered processing)
    existing_items_list = fetch_existing_items(BOARD_ID, GROUP_ID)

    logger.info(f"Reading Excel file: {EXCEL_FILE_PATH}")

    try:
        df = pd.read_excel(EXCEL_FILE_PATH, sheet_name=SHEET_NAME, header=0)

        if df.empty:
            logger.warning("Excel file is empty.")
            return

        first_column_data = df.iloc[:, 0]
        # Keep all rows to preserve alignment, converting NaNs/None to empty strings
        clean_data = [
            str(val).strip() if not pd.isna(val) else ""
            for val in first_column_data
        ]

        logger.info(f"Found {len(clean_data)} rows to process (including empty ones).")

        created_count = 0
        updated_count = 0
        skipped_count = 0
        fail_count = 0

        for i, value_str in enumerate(clean_data):
            if not value_str:
                logger.info(f"Row {i+1}: Empty value in Excel. Skipping to preserve alignment.")
                skipped_count += 1
                continue

            # Prepare column values
            col_vals = {}
            if COLUMN_ID and COLUMN_ID.lower() != "name":
                col_vals[COLUMN_ID] = value_str

            # CHECK IF ITEM EXISTS AT THIS INDEX
            if i < len(existing_items_list):
                # UPDATE EXISTING ITEM
                existing_item = existing_items_list[i]
                item_id = existing_item["id"]
                current_name = existing_item["name"]

                logger.info(
                    f"Row {i+1}: Updating item {i+1}/{len(existing_items_list)} (ID: {item_id}, Name: '{current_name}') with value: '{value_str}'"
                )

                # Only update the specific column, do not change the name
                response = update_monday_item(item_id, col_vals)
                if response and "data" in response and response["data"]:
                    updated_count += 1
                else:
                    logger.error(
                        f" -> Failed to update item: {value_str}. Response: {json.dumps(response, indent=2) if response else 'None'}"
                    )
                    fail_count += 1

            else:
                # CREATE NEW ITEM
                logger.info(f"Row {i+1}: Creating new item: '{value_str}'...")

                # For creation, 'item_name' is passed as the main argument
                response = create_monday_item(
                    item_name=value_str, column_values=col_vals
                )

                if (
                    response
                    and "data" in response
                    and "create_item" in response["data"]
                ):
                    item_id = response["data"]["create_item"]["id"]
                    logger.info(f" -> Created Item ID: {item_id}")
                    created_count += 1
                else:
                    logger.error(f" -> Failed to create item: {value_str}")
                    fail_count += 1

        logger.info("------------------------------------------------")
        logger.info(f"Processing complete.")
        logger.info(f"Created: {created_count}")
        logger.info(f"Updated: {updated_count}")
        logger.info(f"Skipped (No changes needed): {skipped_count}")
        logger.info(f"Failed: {fail_count}")

    except Exception as e:
        logger.exception(f"An unexpected error occurred during processing: {e}")


if __name__ == "__main__":
    process_excel_upload()
