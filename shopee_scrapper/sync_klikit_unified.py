import json
import time
import re
import os
import glob
from common.monday_api import execute_monday_query
from common.logger import get_logger
from shopee_scrapper.sync_store_details import get_latest_raw_file as get_shopee_file

log = get_logger("klikit_unified_sync")

# --- Configuration ---
BOARD_ID = 5025182611
GROUP_ID = "group_mkys1dmf"

# Combined Column Mapping
# We map all necessary columns for a brand here.
CONFIG = {
    "Foodnesia": {
        "shopee_sid": "text_mky9x4kv",
        "shopee_addr": "text_mkypb9j4",
        "shopee_addr_stat": "color_mkys8d7s",
        "shopee_oph_stat": "color_mkysx17g",
        "grab_sid": "text_mky9b8z9",
        "grab_addr": "text_mkyp1rk7",
        "grab_addr_stat": "color_mkys8d7s",  # Note: Shares column with Shopee in provided configs
        "grab_hint": "F2S",
    },
    "WonderFood": {
        "shopee_sid": "text_mky9tgv5",
        "shopee_addr": "text_mkypgpv0",
        "shopee_addr_stat": "color_mkys95tn",
        "shopee_oph_stat": "color_mkysgtbj",
        "grab_sid": "text_mky974s9",
        "grab_addr": "text_mkypgpv0",
        "grab_addr_stat": "color_mkys95tn",
        "grab_hint": "W1",
    },
    "Lokarasa": {
        "shopee_sid": "text_mky9hszn",
        "shopee_addr": "text_mkyp4m9e",
        "shopee_addr_stat": "color_mkysfnjp",
        "shopee_oph_stat": "color_mkysv3nq",
        "grab_sid": "text_mky9pxvr",
        "grab_addr": "text_mkyp4m9e",
        "grab_addr_stat": "color_mkysfnjp",
        "grab_hint": "L1",
    },
    "DoEat": {
        "shopee_sid": "text_mky94yev",
        "shopee_addr": "text_mkyph880",
        "shopee_addr_stat": "color_mkys7bd0",
        "shopee_oph_stat": "color_mkysa5yy",
        "grab_sid": "text_mky9z4ts",
        "grab_addr": "text_mkyph880",
        "grab_addr_stat": "color_mkys7bd0",
        "grab_hint": "DE1",
    },
}

DISPLAY_STATUS_MAP = {1: "Closed", 2: "Open", 3: "Busy"}


def get_latest_grab_file(account_hint):
    """Finds the latest raw Grab JSON file."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.abspath(
        os.path.join(base_dir, "..", "grab_scrapper", "raw_grab_data")
    )
    if not os.path.exists(raw_dir):
        return None
    pattern = os.path.join(raw_dir, f"grabfood_*{account_hint}*.json")
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(reverse=True)
    return files[0]


def normalize_text(text):
    """Removes non-alphanumeric characters for robust comparison."""
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def validate_address(item_name, address):
    """Checks if item name is in address (normalized)."""
    if not address or not item_name:
        return "Invalid"
    return (
        "Valid" if normalize_text(item_name) in normalize_text(address) else "Invalid"
    )


def fetch_monday_items(board_id, group_id, shopee_sid_col, grab_sid_col):
    """Fetches items with Name, Shopee SID, and Grab SID."""
    items = []
    next_cursor = None
    log.info(f"Fetching items from Board {board_id}...")

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
                                column_values(ids: ["{shopee_sid_col}", "{grab_sid_col}"]) {{
                                    id
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
            group_data = response["data"]["boards"][0]["groups"][0]
            items.extend(group_data["items_page"]["items"])
            next_cursor = group_data["items_page"]["cursor"]
            if not next_cursor:
                break
            time.sleep(0.5)
        except Exception as e:
            log.error(f"Error parsing Monday response: {e}")
            break

    return items


def run_unified_sync(browser_session, merchant_task, dry_run=False):
    merchant_name = merchant_task.get("output_name", "")

    # 1. Determine Config
    cfg = None
    for brand, conf in CONFIG.items():
        if brand.lower() in merchant_name.lower():
            cfg = conf
            break

    if not cfg:
        log.warning(f"Skipping Unified Sync: No config found for '{merchant_name}'.")
        return

    log.info(
        f"Starting Unified Klikit Sync for '{merchant_name}'..."
        + (" [DRY RUN]" if dry_run else "")
    )

    # 2. Load Data Sources
    # Shopee Data
    shopee_data = {}
    shopee_file = get_shopee_file(merchant_name)
    if shopee_file:
        try:
            with open(shopee_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
                for s in raw:
                    sid = str(s.get("id", ""))
                    if sid:
                        shopee_data[sid] = {
                            "address": s.get("store_address", ""),
                            "status": s.get("display_status"),
                        }
            log.info(f"Loaded {len(shopee_data)} Shopee stores.")
        except Exception as e:
            log.error(f"Failed to load Shopee file: {e}")

    # Grab Data
    grab_data = {}
    grab_file = get_latest_grab_file(cfg["grab_hint"])
    if grab_file:
        try:
            with open(grab_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
                for s in raw:
                    sid = str(s.get("merchantID", ""))
                    if sid:
                        grab_data[sid] = {"address": s.get("address", "")}
            log.info(f"Loaded {len(grab_data)} Grab stores.")
        except Exception as e:
            log.error(f"Failed to load Grab file: {e}")

    # 3. Fetch Monday Items
    monday_items = fetch_monday_items(
        BOARD_ID, GROUP_ID, cfg["shopee_sid"], cfg["grab_sid"]
    )
    log.info(f"Fetched {len(monday_items)} items from Monday.")

    # 4. Process Items
    updates_count = 0

    for item in monday_items:
        item_id = int(item["id"])
        item_name = item["name"]
        col_vals = {}

        # Extract SIDs from column values
        shopee_sid_val = None
        grab_sid_val = None

        for cv in item.get("column_values", []):
            if cv["id"] == cfg["shopee_sid"]:
                shopee_sid_val = cv["text"].strip()
            elif cv["id"] == cfg["grab_sid"]:
                grab_sid_val = cv["text"].strip()

        # --- Shopee Logic ---
        if shopee_sid_val and shopee_sid_val in shopee_data:
            s_info = shopee_data[shopee_sid_val]

            # Address Validation
            addr = s_info["address"]
            val_res = validate_address(item_name, addr)
            col_vals[cfg["shopee_addr"]] = addr
            col_vals[cfg["shopee_addr_stat"]] = {"label": val_res}

            # OPH Status
            disp_stat = s_info["status"]
            if disp_stat:
                try:
                    stat_int = int(disp_stat)
                    if stat_int in DISPLAY_STATUS_MAP:
                        col_vals[cfg["shopee_oph_stat"]] = {
                            "label": DISPLAY_STATUS_MAP[stat_int]
                        }
                except ValueError:
                    pass

        # --- Grab Logic ---
        if grab_sid_val and grab_sid_val in grab_data:
            g_info = grab_data[grab_sid_val]

            # Address Validation
            addr = g_info["address"]
            val_res = validate_address(item_name, addr)
            col_vals[cfg["grab_addr"]] = addr
            col_vals[cfg["grab_addr_stat"]] = {"label": val_res}

        # --- Execute Update ---
        if col_vals:
            if dry_run:
                log.info(
                    f"  [DRY RUN] Item '{item_name}' ({item_id}) updates: {json.dumps(col_vals)}"
                )
                updates_count += 1
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
                "colVals": json.dumps(col_vals),
            }

            res = execute_monday_query(mutation, variables)
            if res and "data" in res:
                updates_count += 1
                log.info(f"  -> Updated '{item_name}' ({item_id})")
            else:
                log.error(f"  -> Failed to update '{item_name}': {res}")

            time.sleep(0.2)  # Rate limit protection

    log.info(
        f"✅ Unified Sync Complete for {merchant_name}. {'Would have updated' if dry_run else 'Updated'} {updates_count} items."
    )
