import re
import os
import sys
import time
import random
import requests
import json
from datetime import datetime

# Add project root to path to import common and config modules
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, project_root)

from common.logger import get_logger
from common.monday_utils import fetch_board_items
from dotenv import load_dotenv
from common.notifications import send_discord_notification
from modules.shopee.force_open.config_loader import load_config
from modules.shopee.api_utils import (
    get_auth_tokens,
    get_shopee_headers,
)
from modules.shopee.browser_session import BrowserSession
from common.monday_utils import filter_items_by_check_level

log = get_logger("force_open")
log.propagate = False
load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Load Configuration
config = load_config()
MONDAY_BOARD_ID = config.get("MONDAY_BOARD_ID")
GROUP_ID = config.get("GROUP_ID")
CHECK_COL_ID = config.get("CHECK_COL_ID")
CLOSED_REQ_COL_ID = config.get("CLOSED_REQ_COL_ID")
MERCHANT_COL_MAP = config.get("MERCHANT_COL_MAP", {})
MERCHANT_SHORT_NAME_COL_MAP = config.get("MERCHANT_SHORT_NAME_COL_MAP", {})
STORE_ID_COL_MAP = config.get("STORE_ID_COL_MAP", {})


# API Configuration
SHOPEE_API_BASE = "https://foody.shopee.co.id"
API_TIMEOUT = 5  # Reduced from 10s for faster timeouts
RATE_LIMIT_DELAY_MIN = 0.3  # Reduced from 2s for faster processing
RATE_LIMIT_DELAY_MAX = 0.7  # Reduced from 5s for faster processing
MAX_PARALLEL_STORES = 1


def process_store_via_api(store_data: dict, tob_token: str, entity_id: str) -> dict:
    action = store_data["action"]
    short_name = store_data["short_name"]

    headers = get_shopee_headers(tob_token, entity_id)

    try:
        if action == "OPEN":
            url = f"{SHOPEE_API_BASE}/api/seller/store/opening-status/action/open"
            log.debug(f"[API_CALL] Calling API: POST {url}")
            response = requests.post(url, json={}, headers=headers, timeout=API_TIMEOUT)
        else:  # CLOSE
            url = f"{SHOPEE_API_BASE}/api/seller/store/opening-status/action/pause"
            log.debug(f"[API_CALL] Calling API: POST {url}")
            response = requests.post(
                url, json={"close_all_day": True}, headers=headers, timeout=API_TIMEOUT
            )

        data = response.json()

        if data.get("code") == 0:
            log.info(f"[SUCCESS] {action} success: {short_name}")
            return {"success": True, "action": action}
        else:
            error_msg = data.get("msg", "Unknown error")
            log.error(f"[API_ERROR] API error ({action}): {error_msg}")
            return {"success": False, "error": error_msg}

    except requests.exceptions.Timeout:
        log.error(f"[TIMEOUT] API timeout during {action} for {short_name}")
        return {"success": False, "error": "API timeout"}
    except requests.exceptions.ConnectionError as e:
        log.error(f"[CONN_ERROR] Connection error: {e}")
        return {"success": False, "error": "Connection error"}
    except Exception as e:
        log.error(f"[FAILED] Failed to {action} store: {e}")
        return {"success": False, "error": str(e)}


def get_store_status_via_api(
    store_long_name: str, tob_token: str, merchant_entity_id: str, target_store_id: str
) -> dict:
    """Fetch store status from Shopee API.

    Uses the store search endpoint to get the current display_status.
    """
    headers = get_shopee_headers(tob_token, merchant_entity_id)

    # Clean store name: strip whitespace
    clean_store_name = store_long_name.strip()

    payload = {
        "filter": {"store_name": clean_store_name},
        "page_no": 1,
        "page_size": 50,
    }

    display_status_map = {1: "Closed", 2: "Open", 3: "Busy"}

    try:
        url = f"{SHOPEE_API_BASE}/api/seller/stores/search"
        log.debug(f"[SEARCH] Searching store: '{clean_store_name}'")
        response = requests.post(
            url, json=payload, headers=headers, timeout=API_TIMEOUT
        )
        data = response.json()

        if data.get("code") == 0:
            resp_data = data.get("data") or {}

            # API returns store_basic_info_list, not stores
            stores = resp_data.get("store_basic_info_list", [])
            target_store = None
            # 1. Try to find exact match by ID
            for store in stores:
                # Convert both to strings for comparison to be safe
                if str(store.get("id")) == str(target_store_id):
                    target_store = store
                    log.debug(f"[MATCH] Found store by ID: {target_store_id}")
                    break

            # 2. If no ID match, fallback to first result
            if not target_store and stores:
                log.warning(
                    f"[WARNING] Store ID {target_store_id} not found in search results. Using first result: {stores[0].get('name')} (ID: {stores[0].get('id')})"
                )
                target_store = stores[0]

            if target_store:
                display_status = target_store.get("display_status")
                status_name = display_status_map.get(display_status, "Unknown")
                found_store_name = target_store.get("name", "Unknown")
                found_store_id = target_store.get("id", "Unknown")

                log.debug(
                    f"[SUCCESS] Found store: '{found_store_name}' (ID: {found_store_id}) → Status: {status_name} ({display_status})"
                )
                return {
                    "found": True,
                    "display_status": display_status,
                    "display_status_name": status_name,
                }
            else:
                log.warning(
                    f"[NOT_FOUND] Store not found in search results: '{clean_store_name}'"
                )
                # Dump data to debug why list is empty
                log.debug(f"[DEBUG_DATA] API Response Data: {str(resp_data)[:200]}")
                return {"found": False, "error": "Store not found in search results"}
        else:
            error_msg = data.get("msg", "Unknown error")
            log.warning(f"[API_ERROR] API error while checking status: {error_msg}")
            return {"found": False, "error": error_msg}

    except Exception as e:
        log.error(f"[FAILED] Failed to get store status for '{clean_store_name}': {e}")
        # Add traceback for deeper debugging if needed
        import traceback

        log.debug(traceback.format_exc())
        return {"found": False, "error": str(e)}


def run_force_open(
    session, merchant_task, scale_level=None, dry_run=False, driver_creator=None
):
    """Run force-open/close using Shopee internal API (no Selenium UI flows).

    - `session` is used only to extract browser cookies for auth tokens.
    - `merchant_task` contains merchant mapping used to find Monday columns.
    Returns a stats dictionary summarizing actions taken.
    """
    if scale_level is None:
        scale_level = config.get("SCALE_LEVEL", 1)

    log.info(f"Starting Force Open/Close Task. Scale Level: {scale_level}")

    # 1. Get merchant info & column IDs
    merchant_name = merchant_task.get("output_name", "")
    target_long_col_id = MERCHANT_COL_MAP.get(merchant_name)
    target_short_col_id = MERCHANT_SHORT_NAME_COL_MAP.get(merchant_name)
    target_store_id_col_id = STORE_ID_COL_MAP.get(merchant_name)  # NEW!

    if not target_long_col_id:
        log.warning(f"Could not map merchant '{merchant_name}'. Skipping.")
        return {}

    # 2. Fetch Monday data
    log.info(f"Fetching data from Monday.com for {merchant_name}...")
    items = fetch_board_items(MONDAY_BOARD_ID, GROUP_ID)

    filtered = filter_items_by_check_level(items, CHECK_COL_ID, scale_level)

    stores_to_process = []
    for item, col_vals in filtered:
        s_long_name = col_vals.get(target_long_col_id) or ""
        s_short_name = col_vals.get(target_short_col_id) or ""
        s_store_id = col_vals.get(target_store_id_col_id) or ""

        if not s_short_name.strip():
            s_short_name = s_long_name

        action = "OPEN"
        if col_vals.get(CLOSED_REQ_COL_ID, "").strip() == "Closed":
            action = "CLOSE"

        if s_long_name and s_store_id:
            stores_to_process.append(
                {
                    "long_name": s_long_name.strip(),
                    "short_name": s_short_name.strip(),
                    "store_id": s_store_id.strip(),
                    "action": action,
                    "scale_level_str": col_vals.get(CHECK_COL_ID, "").strip(),
                }
            )

    log.info(f"Found {len(stores_to_process)} stores to process")

    if not stores_to_process:
        return {}

    stats = {
        "forced_open": [],
        "forced_close": [],
        "already_open": [],
        "closed_in_regular_hours": [],
        "failed": [],
    }
    tob_token, merchant_entity_id = get_auth_tokens(
        driver=session.driver, merchant_name=merchant_name
    )
    if not tob_token:
        log.warning(
            "Initial token extraction failed. Trying fallback with temporary browser session..."
        )
        temp_session = None
        try:
            temp_session = BrowserSession(headless=False)
            if temp_session.driver and temp_session.ensure_logged_in():
                # Attempt extraction using the fresh driver and request JSON result (ensures save)
                tokens = get_auth_tokens(
                    driver=temp_session.driver,
                    return_json=True,
                    merchant_name=merchant_name,
                )
                if tokens and tokens.get("shopee_tob_token"):
                    tob_token = tokens.get("shopee_tob_token")
                    merchant_entity_id = tokens.get("shopee_tob_entity_id") or ""
                    log.info("Fallback extraction succeeded and tokens saved to cache.")
                else:
                    log.error("Fallback extraction did not return tokens.")
            else:
                log.error("Fallback browser session initialization or login failed.")
        except Exception as e:
            log.error(f"Fallback extraction error: {e}")
        finally:
            if temp_session:
                try:
                    temp_session.quit()
                except Exception:
                    pass

    if not tob_token:
        log.error("Failed to extract tob_token. Cannot proceed.")
        return stats

    if not merchant_entity_id:
        log.warning("Merchant entity_id not found. Search API might fail.")

    log.info("Authentication successful")
    log.debug(f"tob_token: {tob_token[:20]}... Merchant ID: {merchant_entity_id}")

    log.info(
        f"Processing {len(stores_to_process)} stores via API (batch size: {MAX_PARALLEL_STORES})..."
    )

    import concurrent.futures

    def process_single_store(args):
        """Process a single store and return results."""
        i, store_data, total = args
        store_name = store_data["long_name"]
        short_name = store_data["short_name"]
        store_id = store_data["store_id"]
        monday_action = store_data["action"]
        scale_level_str = store_data.get("scale_level_str", "Unknown")
        store_name_for_search = store_name

        log.info(f"\n[{i+1}/{total}] Checking: {store_name} (Monday: {monday_action})")
        log.debug(f"Store ID: {store_id} | Short Name: {short_name}")

        try:
            status_result = get_store_status_via_api(
                store_name_for_search, tob_token, merchant_entity_id, store_id
            )

            if not status_result.get("found"):
                log.error(f"Could not fetch store status. Skipping.")
                return ("failed", store_name, scale_level_str)

            actual_status = status_result.get("display_status")
            action_to_take = None

            if monday_action == "OPEN":
                if actual_status == 1:
                    log.info(f"{store_name} is Closed (operational hours). No action.")
                    return ("closed_in_regular_hours", short_name, scale_level_str)
                elif actual_status == 2:
                    log.info(f"{store_name} is already Open. No action.")
                    return ("already_open", short_name, scale_level_str)
                elif actual_status == 3:
                    action_to_take = "OPEN"
                    log.info(f"{store_name} is Busy. Will force OPEN.")

            elif monday_action == "CLOSE":
                if actual_status == 1:
                    log.info(f"{store_name} is Closed (operational hours). No action.")
                    return ("closed_in_regular_hours", short_name, scale_level_str)
                elif actual_status == 2:
                    action_to_take = "CLOSE"
                    log.info(f"{store_name} is Open. Will force CLOSE.")
                elif actual_status == 3:
                    log.info(f"{store_name} is already closed. No action.")
                    return ("closed_in_regular_hours", short_name, scale_level_str)

            if action_to_take and not dry_run:
                result = process_store_via_api(
                    store_data={**store_data, "action": action_to_take},
                    tob_token=tob_token,
                    entity_id=store_id,
                )
                if result["success"]:
                    return (
                        f"forced_{action_to_take.lower()}",
                        short_name,
                        scale_level_str,
                    )
                else:
                    log.error(f"{store_name} - {result.get('error')}")
                    return ("failed", store_name, scale_level_str)
            elif action_to_take and dry_run:
                log.info(f"[DRY_RUN] Would {action_to_take}")
                return (
                    f"forced_{action_to_take.lower()}",
                    f"{short_name} (DRY_RUN)",
                    scale_level_str,
                )

            return ("no_action", short_name, scale_level_str)

        except Exception as e:
            log.error(f"Error: {e}")
            return ("failed", store_name, scale_level_str)

    # Process stores in parallel batches
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_PARALLEL_STORES
    ) as executor:
        tasks = [
            (i, store_data, len(stores_to_process))
            for i, store_data in enumerate(stores_to_process)
        ]

        for future in concurrent.futures.as_completed(
            [executor.submit(process_single_store, task) for task in tasks]
        ):
            status_type, item_name, item_level = future.result()

            if status_type == "forced_open":
                stats["forced_open"].append((item_name, item_level))
            elif status_type == "forced_close":
                stats["forced_close"].append((item_name, item_level))
            elif status_type == "already_open":
                stats["already_open"].append((item_name, item_level))
            elif status_type == "closed_in_regular_hours":
                stats["closed_in_regular_hours"].append((item_name, item_level))
            elif status_type == "failed":
                stats["failed"].append((item_name, item_level))

                time.sleep(random.uniform(RATE_LIMIT_DELAY_MIN, RATE_LIMIT_DELAY_MAX))

    # Send Discord notification only if there are forced opens/closes
    if stats["forced_open"] or stats["forced_close"]:
        log.info("Sending Discord notification...")

        summary_message = (
            f"**Merchant:** {merchant_name}\n"
            f"**Total Processed:** {len(stores_to_process)}\n"
        )

        def format_field_value(items_with_level, max_chars=1000):
            if not items_with_level:
                return "None"

            # Group by level
            grouped = {}
            for name, level in items_with_level:
                if level not in grouped:
                    grouped[level] = []
                grouped[level].append(name)

            # Sort levels (Yes 1, Yes 2, ...)
            sorted_levels = sorted(grouped.keys())

            lines = []
            for level in sorted_levels:
                stores = grouped[level]
                store_str = ", ".join(stores)
                lines.append(f"{level}: {store_str}")

            full_text = "\n".join(lines)
            if len(full_text) > max_chars:
                return full_text[: max_chars - 3] + "..."
            return full_text

        fields = []

        fields.append(
            {
                "name": f"✅ Force Open ({len(stats['forced_open'])})",
                "value": format_field_value(stats["forced_open"]),
                "inline": False,
            }
        )

        fields.append(
            {
                "name": f"❌ Force Close ({len(stats['forced_close'])})",
                "value": format_field_value(stats["forced_close"]),
                "inline": False,
            }
        )

        other_categories = [
            ("ℹ️ Already Open", stats["already_open"]),
            ("⏰ Closed in Regular Hours", stats["closed_in_regular_hours"]),
        ]

        for emoji_name, items in other_categories:
            fields.append(
                {
                    "name": f"{emoji_name} ({len(items)})",
                    "value": format_field_value(items),
                    "inline": False,
                }
            )

        send_discord_notification(
            DISCORD_WEBHOOK_URL,
            f"Shopee Force Open Report {'[DRY RUN]' if dry_run else ''}",
            summary_message,
            fields=fields,
            color=5814783 if not stats["failed"] else 15158332,
        )
        log.info("Discord notification sent")
    else:
        log.info("No forced opens/closes. Skipping Discord notification.")

    log.info(
        f"Completed - Forced Open: {len(stats['forced_open'])}, "
        f"Forced Close: {len(stats['forced_close'])}, "
        f"Already Open: {len(stats['already_open'])}, "
        f"Closed in Regular Hours: {len(stats['closed_in_regular_hours'])}, "
        f"Failed: {len(stats['failed'])}"
    )

    return stats
