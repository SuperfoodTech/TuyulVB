import json
import time
from common.monday_api import execute_monday_query
from common.logger import get_logger
from shopee_scrapper.sync_store_details import get_latest_raw_file

log = get_logger("oph_klikit_sync")

# --- Configuration ---
BOARD_ID = 5025182611
GROUP_ID = "group_mkys1dmf"

# Column Mappings per Brand
COLUMN_MAPPING = {
    "Foodnesia": {
        "sid": "text_mky9x4kv",
        "status_col": "color_mkysx17g",
    },
    "WonderFood": {
        "sid": "text_mky9tgv5",
        "status_col": "color_mkysgtbj",
    },
    "Lokarasa": {
        "sid": "text_mky9hszn",
        "status_col": "color_mkysv3nq",
    },
    "DoEat": {
        "sid": "text_mky94yev",
        "status_col": "color_mkysa5yy",
    },
}

DISPLAY_STATUS_MAP = {1: "Closed", 2: "Open", 3: "Busy"}


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


def run_oph_sync(browser_session, merchant_task, dry_run=False):
    merchant_name = merchant_task.get("output_name", "")

    # Determine which brand mapping to use
    mapping = None
    for brand, cols in COLUMN_MAPPING.items():
        if brand.lower() in merchant_name.lower():
            mapping = cols
            break

    if not mapping:
        log.warning(
            f"Skipping OPH sync: No column mapping found for merchant '{merchant_name}'."
        )
        return

    log.info(
        f"Starting OPH Sync for '{merchant_name}'..."
        + (" [DRY RUN]" if dry_run else "")
    )

    # 1. Load JSON Data
    raw_file = get_latest_raw_file(merchant_name)
    if not raw_file:
        log.error(f"Skipping: No raw data file found for '{merchant_name}'.")
        return

    try:
        with open(raw_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        log.error(f"Failed to load JSON file: {e}")
        return

    # Create Lookup: SID -> Status Label
    json_lookup = {}
    for store in raw_data:
        s_id = str(store.get("id", ""))
        disp_status = store.get("display_status")
        if s_id and disp_status:
            try:
                status_int = int(disp_status)
                if status_int in DISPLAY_STATUS_MAP:
                    json_lookup[s_id] = DISPLAY_STATUS_MAP[status_int]
            except ValueError:
                pass

    # 2. Fetch Monday Items
    monday_items_map = fetch_monday_items(BOARD_ID, GROUP_ID, mapping["sid"])

    # 3. Update Monday
    updates_count = 0
    for sid, items in monday_items_map.items():
        if sid in json_lookup:
            status_label = json_lookup[sid]
            for item in items:
                if dry_run:
                    log.info(
                        f"  [DRY RUN] Would update '{item['name']}' (ID: {item['id']}) -> Status: {status_label}"
                    )
                    continue

                mutation = """mutation ($itemId: ID!, $boardId: ID!, $colVals: JSON!) { change_multiple_column_values (item_id: $itemId, board_id: $boardId, column_values: $colVals) { id } }"""
                variables = {
                    "itemId": int(item["id"]),
                    "boardId": BOARD_ID,
                    "colVals": json.dumps(
                        {mapping["status_col"]: {"label": status_label}}
                    ),
                }
                if execute_monday_query(mutation, variables):
                    updates_count += 1
                    log.info(
                        f"  -> Updated '{item['name']}' (ID: {item['id']}) -> Status: {status_label}"
                    )
                time.sleep(0.2)

    log.info(
        f"✅ OPH Sync complete for {merchant_name}. {'Would have updated' if dry_run else 'Updated'} {updates_count} items."
    )
