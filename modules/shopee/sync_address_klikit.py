import json
import time
import re
from common.monday_api import execute_monday_query
from common.logger import get_logger
from modules.shopee.sync_store_details import get_latest_raw_file

log = get_logger("address_validation")

# --- Configuration ---
BOARD_ID = 5025182611
GROUP_ID = "group_mkys1dmf"

# Column Mappings per Brand
COLUMN_MAPPING = {
    "Foodnesia": {
        "sid": "text_mky9x4kv",
        "address": "text_mkypb9j4",
        "status": "color_mkys8d7s",
    },
    "WonderFood": {
        "sid": "text_mky9tgv5",
        "address": "text_mkypgpv0",
        "status": "color_mkys95tn",
    },
    "Lokarasa": {
        "sid": "text_mky9hszn",
        "address": "text_mkyp4m9e",
        "status": "color_mkysfnjp",
    },
    "DoEat": {
        "sid": "text_mky94yev",
        "address": "text_mkyph880",
        "status": "color_mkys7bd0",
    },
}


def fetch_monday_items(board_id, group_id, sid_column_id):
    """
    Fetches all items from the board/group, retrieving ID, Name, and the specific SID column.
    """
    items_map = {}
    next_cursor = None

    log.info(f"Fetching items from Board {board_id}, Group {group_id}...")

    while True:
        cursor_arg = f', cursor: "{next_cursor}"' if next_cursor else ""
        query = f"""
            query($boardId: [ID!], $groupId: [String!]) {{
                boards(ids: $boardId) {{
                    groups(ids: $groupId) {{
                        items_page(limit: 100{cursor_arg}) {{
                            cursor
                            items {{
                                id
                                name
                                column_values(ids: ["{sid_column_id}"]) {{
                                    text
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        """
        variables = {"boardId": [board_id], "groupId": [group_id]}
        response = execute_monday_query(query, variables)

        try:
            if "errors" in response:
                log.error(f"Monday API Error: {response['errors']}")
                break

            boards_data = response.get("data", {}).get("boards", [])
            if not boards_data:
                log.error("No board data returned.")
                break

            group_data = boards_data[0]["groups"][0]
            items_page = group_data["items_page"]
            items = items_page["items"]
            next_cursor = items_page["cursor"]

            for item in items:
                # Extract SID
                sid_val = None
                col_vals = item.get("column_values", [])
                if col_vals and col_vals[0].get("text"):
                    sid_val = col_vals[0]["text"].strip()

                if sid_val:
                    if sid_val not in items_map:
                        items_map[sid_val] = []
                    items_map[sid_val].append({"id": item["id"], "name": item["name"]})

            if not next_cursor:
                break

            time.sleep(0.5)

        except (KeyError, IndexError, TypeError) as e:
            log.error(f"Error parsing Monday response: {e}")
            break

    return items_map


def run_address_validation(browser_session, merchant_task, dry_run=False):
    """
    Main execution function for address validation.
    Matches Monday items (Left) with JSON data (Right) based on SID.
    Updates Address and Status on Monday.
    """
    merchant_name = merchant_task.get("output_name", "")

    # Determine which brand mapping to use
    mapping = None
    for brand, cols in COLUMN_MAPPING.items():
        if brand.lower() in merchant_name.lower():
            mapping = cols
            break

    if not mapping:
        log.warning(
            f"Skipping address validation: No column mapping found for merchant '{merchant_name}'."
        )
        return

    log.info(
        f"Starting Address Validation for '{merchant_name}' on Board {BOARD_ID}..."
        + (" [DRY RUN]" if dry_run else "")
    )

    # 1. Load JSON Data
    raw_file = get_latest_raw_file(merchant_name)
    if not raw_file:
        log.error(
            f"Skipping: No raw data file found for '{merchant_name}'. Run extraction first."
        )
        return

    log.info(f"Loading raw data from: {raw_file}")
    try:
        with open(raw_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        log.error(f"Failed to load JSON file: {e}")
        return

    # Create Lookup: SID -> Address
    json_lookup = {}
    for store in raw_data:
        s_id = str(store.get("id", ""))
        s_addr = store.get("store_address", "")
        if s_id and s_addr:
            json_lookup[s_id] = s_addr

    log.info(f"Loaded {len(json_lookup)} stores from JSON.")

    # 2. Fetch Monday Items
    monday_items_map = fetch_monday_items(BOARD_ID, GROUP_ID, mapping["sid"])
    log.info(f"Found {len(monday_items_map)} items on Monday with SID populated.")

    # 3. Validate and Update
    updates_count = 0

    for sid, items in monday_items_map.items():
        if sid in json_lookup:
            address = json_lookup[sid]

            for item in items:
                item_id = int(item["id"])
                item_name = item["name"]

                # Validation: Check if Item Name is in Address (Case Insensitive)
                # Normalize by removing non-alphanumeric characters to handle cases like "Minang Agung - Klojen" vs "Minang Agung Klojen"
                norm_name = re.sub(r"[^a-z0-9]", "", item_name.lower())
                norm_address = re.sub(r"[^a-z0-9]", "", address.lower())
                is_valid = norm_name in norm_address if norm_name else False
                status_label = "Valid" if is_valid else "Invalid"

                # Prepare Update
                column_values = {
                    mapping["address"]: address,
                    mapping["status"]: {"label": status_label},
                }

                if dry_run:
                    log.info(
                        f"  [DRY RUN] Would update Item '{item_name}' (ID: {item_id}): Address='{address}', Status={status_label}"
                    )
                    continue

                mutation = """
                    mutation ($itemId: ID!, $boardId: ID!, $colVals: JSON!) {
                        change_multiple_column_values (item_id: $itemId, board_id: $boardId, column_values: $colVals) {
                            id
                        }
                    }
                """
                variables = {
                    "itemId": item_id,
                    "boardId": BOARD_ID,
                    "colVals": json.dumps(column_values),
                }

                result = execute_monday_query(mutation, variables)
                if result:
                    updates_count += 1
                    log.info(
                        f"  -> Updated Item '{item_name}' (ID: {item_id}): Status={status_label}"
                    )

                time.sleep(0.2)

    log.info(
        f"✅ Address validation complete for {merchant_name}. {'Would have updated' if dry_run else 'Updated'} {updates_count} items."
    )
