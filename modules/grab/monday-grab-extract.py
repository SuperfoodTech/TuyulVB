"""Extract merchant listings from Grab and sync to Monday.com

Uses the browser login flow in `modules.grab.browser_session` to obtain cookies
per portal, calls the Grab merchant search endpoint with pagination, saves raw
responses and upserts items into Monday groups defined in `config.settings_grab`.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List

import requests

from common.logger import get_logger
from common import monday_utils
from common.monday_api import execute_monday_query
from common.config import EnvConfig
from common.notifications import send_discord_notification

from config import settings_grab
from config import credentials_grab
from modules.grab import browser_session
from modules.grab.api_utils import cookie_dict_to_string, cookie_string_to_dict

log = get_logger("monday_grab_extract")
log.propagate = False


# Portal selection and credential helpers are provided by `modules.grab.browser_session`.
def choose_portals() -> List[str]:
    available = browser_session.get_available_portals()
    if not available:
        log.error("No portals available in credentials; exiting")
        return []
    return browser_session.select_portals_interactive(available)


def get_creds_for(portal: str) -> Dict[str, str]:
    return credentials_grab.ACCOUNT_CREDS.get(portal, {}) or {}


def fetch_merchants_for_portal(
    cookie_map: Dict[str, str], token: str = None
) -> tuple[List[dict], str]:
    url = settings_grab.TARGET_API_URL
    merchants: List[dict] = []
    merchant_group_id = None
    offset = 0
    limit = 100

    # build requests session with cookies
    s = requests.Session()
    for k, v in cookie_map.items():
        if v:
            s.cookies.set(k, v)

    headers = {
        "accept": "application/json",
        "accept-language": "en",
        "origin": "https://merchant.grab.com",
        "referer": "https://merchant.grab.com/",
        "requestsource": "troyPortal",
        "dnt": "1",
        "x-country-code": "ID",
        "x-gfc-country": "ID",
        "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        ),
    }
    if token:
        headers["x-hydra-jwt"] = token

    use_fallback = False

    while True:
        if use_fallback:
            current_url = settings_grab.SINGLE_OUTLET_CHECK_URL
            params = {
                "offset": offset,
                "limit": limit,
                "isWithItemPhotoCount": "true",
            }
        else:
            current_url = url
            params = {
                "offset": offset,
                "limit": limit,
                "search": "",
                "includeItemsWithoutPhotosCount": "true",
                "includeInactive": "true",
                "modelType": "integrated",
                "asc": "true",
                "cityIDs[]": "ALL",
                "includeMenuGroupV2ID": "false",
            }

        log.info(f"Hitting endpoint with offset={offset}, limit={limit}")
        try:
            r = s.get(current_url, params=params, headers=headers, timeout=30)
            r.raise_for_status()
            body = r.json()
        except requests.exceptions.HTTPError as e:
            if not use_fallback and e.response.status_code >= 500:
                log.warning(
                    f"Primary API failed with {e.response.status_code}, switching to fallback URL: {settings_grab.SINGLE_OUTLET_CHECK_URL}"
                )
                use_fallback = True
                continue
            log.exception("Failed fetching merchants: %s", e)
            break
        except Exception as e:
            log.exception("Failed fetching merchants: %s", e)
            break

        if merchant_group_id is None:
            merchant_group_id = body.get("merchantGroupID")

        page_merchants = body.get("merchants") or []
        merchants.extend(page_merchants)

        log.info(
            "Received %d merchants (total %d)", len(page_merchants), len(merchants)
        )

        # final page detection: less than requested page size
        if len(page_merchants) < limit:
            break

        offset += limit
        time.sleep(0.5)

    return merchants, merchant_group_id


def save_raw(portal: str, data: dict):
    out_dir = os.path.join(os.getcwd(), "data", "cache")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fname = f"grab_merchants_{portal}_{ts}.json"
    path = os.path.join(out_dir, fname)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info("Saved raw data to %s", path)
    except Exception:
        log.exception("Failed saving raw data to %s", path)


def sync_to_monday(
    portal: str, group_id: str, merchants: List[dict], merchant_group_id: str = None
):
    board_id = settings_grab.MONDAY_BOARD_ID

    # fetch existing items from this group and build map by Store ID column
    column_ids = [
        "text_mkvc896g",
        "text_mkzk8gg2",
        "color_mkvztyew",
        "long_text_mkzk2apc",
    ]
    log.info("Fetching existing items for group %s", group_id)
    existing = monday_utils.get_all_items_from_group(board_id, group_id, column_ids)
    existing_map = {}
    for it in existing:
        # find store id in column_values
        cols = it.get("column_values", [])
        store_id = ""
        for cv in cols:
            if cv.get("id") == "text_mkvc896g":
                store_id = (cv.get("text") or "").strip()
                break
        if store_id:
            existing_map[store_id] = it

    # Normalize merchant IDs to strings so comparison with existing store text values works
    merchant_ids = {
        str(m.get("merchantID")) for m in merchants if m.get("merchantID") is not None
    }

    # detect stale items: present on board but not in freshly fetched merchants
    stale_items = [it for sid, it in existing_map.items() if sid not in merchant_ids]
    log.info(
        "Group %s: %d existing, %d fresh, %d stale",
        group_id,
        len(existing),
        len(merchants),
        len(stale_items),
    )

    # Deletion of stale items moved to run after upserts so updates/creates run first

    # Upsert merchants
    log.info("Starting upsert for %d merchants", len(merchants))
    updated_count = 0
    created_count = 0
    skipped_count = 0
    failed_count = 0

    # --- Begin: Compare for discrepancies and log details (adapted from extract_raw.py) ---
    discrepancy_items = []
    log.info("  Comparing data for discrepancies...")
    for m in merchants:
        mid = m.get("merchantID")
        mgid = merchant_group_id or ""
        addr = m.get("address") or ""

        raw_status = m.get("status")
        if raw_status == "Yes":
            status = "Active"
        elif raw_status == "No":
            status = "Inactive"
        else:
            status = (raw_status or "").capitalize()
        desired_state = {
            "text_mkzk8gg2": mgid,
            "text_mkvc896g": mid,
            "color_mkvztyew": status,
            "long_text_mkzk2apc": addr,
        }
        key_mid = str(mid)
        if key_mid in existing_map:
            item = existing_map[key_mid]
            existing_cols = {
                cv.get("id"): cv.get("text") for cv in item.get("column_values", [])
            }
            diff_fields = []
            for cid, desired in desired_state.items():
                existing_text = existing_cols.get(cid) or ""
                if cid == "color_mkvztyew":
                    if (existing_text or "") != (desired or ""):
                        diff_fields.append(cid)
                else:
                    if (existing_text or "") != (desired or ""):
                        diff_fields.append(cid)
            if diff_fields:
                discrepancy_items.append(
                    {
                        "merchantID": mid,
                        "merchantName": m.get("merchantName", ""),
                        "fields": diff_fields,
                    }
                )
    if not discrepancy_items:
        log.info("  ✅ No discrepancies found. Monday is up to date.")
    else:
        log.info(
            f"  Found {len(discrepancy_items)} items to update (discrepancies detected between Monday and Grab data)."
        )
    # --- End: Compare for discrepancies and log details ---

    for idx, m in enumerate(merchants, start=1):
        mid = m.get("merchantID")
        mname = m.get("merchantName") or ""
        mgid = merchant_group_id or ""
        addr = m.get("address") or ""

        raw_status = m.get("status")
        if raw_status == "Yes":
            status = "Active"
        elif raw_status == "No":
            status = "Inactive"
        else:
            status = (raw_status or "").capitalize()

        # Build the desired state for comparison
        desired_state = {
            "text_mkzk8gg2": mgid,
            "text_mkvc896g": mid,
            "color_mkvztyew": status,
            "long_text_mkzk2apc": addr,
        }

        # Use string key for lookup consistency
        key_mid = str(mid)

        if key_mid in existing_map:
            item = existing_map[key_mid]
            item_id = item.get("id")
            # Build map of existing column values (id -> text)
            existing_cols = {
                cv.get("id"): cv.get("text") for cv in item.get("column_values", [])
            }

            col_changes = {}
            for cid, desired in desired_state.items():
                # For status (color_mkvztyew), compare label text
                if cid == "color_mkvztyew":
                    existing_text = existing_cols.get(cid) or ""
                    if (existing_text or "") != (desired or ""):
                        col_changes[cid] = {"label": desired} if desired else None
                else:
                    existing_text = existing_cols.get(cid) or ""
                    if (existing_text or "") != (desired or ""):
                        col_changes[cid] = desired

            if col_changes:
                log.debug(
                    "Updating item %s for store %s with changes: %s",
                    item_id,
                    mid,
                    list(col_changes.keys()),
                )
                mutation = """
                mutation changeCols($itemId: ID!, $boardId: ID!, $colVals: JSON!) {
                    change_multiple_column_values(item_id: $itemId, board_id: $boardId, column_values: $colVals) { id }
                }
                """
                variables = {
                    "itemId": str(item_id),
                    "boardId": str(board_id),
                    "colVals": json.dumps(col_changes),
                }
                resp = execute_monday_query(mutation, variables, max_retries=3)
                if resp is None:
                    log.error("Update failed (no response) for item %s", item_id)
                    failed_count += 1
                else:
                    if "errors" in resp:
                        log.error(
                            "Failed updating item %s: %s", item_id, resp.get("errors")
                        )
                        failed_count += 1
                    else:
                        updated_count += 1
            else:
                log.debug(
                    "No column changes for item %s (store %s); skipping update",
                    item.get("id"),
                    mid,
                )
                skipped_count += 1
        else:
            # Create new item if not found in Monday
            log.debug("Creating new item for store %s in group %s", mid, group_id)
            col_values = {
                "text_mkzk8gg2": mgid,
                "text_mkvc896g": mid,
                "color_mkvztyew": {"label": status} if status else None,
                "long_text_mkzk2apc": addr,
            }
            # Clean None values
            col_values = {k: v for k, v in col_values.items() if v is not None}
            mutation = """
            mutation createItem($boardId: ID!, $groupId: String!, $itemName: String!, $colVals: JSON!) {
                create_item(board_id: $boardId, group_id: $groupId, item_name: $itemName, column_values: $colVals) { id }
            }
            """
            variables = {
                "boardId": str(board_id),
                "groupId": group_id,
                "itemName": mname or key_mid,
                "colVals": json.dumps(col_values),
            }
            resp = execute_monday_query(mutation, variables, max_retries=3)
            if resp is None:
                log.error("Create failed (no response) for merchant %s", mid)
                failed_count += 1
            else:
                if "errors" in resp:
                    log.error(
                        "Failed creating item for %s: %s", mid, resp.get("errors")
                    )
                    failed_count += 1
                else:
                    created_count += 1

        # Log progress every 50 items to show activity
        if idx % 50 == 0:
            log.info(
                "Upsert progress: %d/%d (created=%d updated=%d skipped=%d failed=%d)",
                idx,
                len(merchants),
                created_count,
                updated_count,
                skipped_count,
                failed_count,
            )

    # Delete stale items from Monday (hard delete)
    if stale_items:
        log.warning(
            "Deleting %d stale items from Monday group %s", len(stale_items), group_id
        )
        batch_size = 50
        for i in range(0, len(stale_items), batch_size):
            batch = stale_items[i : i + batch_size]
            mutation_parts = []
            variables = {}
            var_defs = []
            for j, item in enumerate(batch):
                item_id = item.get("id")
                if item_id is None:
                    continue
                var_name = f"itemId{j}"
                var_defs.append(f"${var_name}: ID!")
                mutation_parts.append(
                    f"delete_{j}: delete_item(item_id: ${var_name}) {{ id }}"
                )
                variables[var_name] = str(item_id)

            if mutation_parts:
                full_mutation = (
                    f"mutation({', '.join(var_defs)}) {{ {' '.join(mutation_parts)} }}"
                )
                log.info("Deleting stale batch %d-%d", i, i + len(batch) - 1)
                resp = execute_monday_query(full_mutation, variables)
                if resp and "errors" in resp:
                    log.error("Error deleting stale batch: %s", resp.get("errors"))
                time.sleep(1.0)
    log.info(
        "Upsert complete: created=%d updated=%d skipped=%d failed=%d",
        created_count,
        updated_count,
        skipped_count,
        failed_count,
    )


def main(headless: bool = False):
    portals = choose_portals()
    if not portals:
        log.info("No portals selected; exiting")
        return

    driver = None
    try:
        driver = browser_session.launch_driver(headless=headless)

        for i, portal_key in enumerate(portals):
            creds = get_creds_for(portal_key)
            username = creds.get("username")
            password = creds.get("password")

            if not username or not password:
                log.error("Missing credentials for portal %s", portal_key)
                continue

            log.info("Log Start Processing: %s", portal_key)
            log.info("Login: %s", portal_key)

            # Use browser_session to login
            if not browser_session.login_to_portal(driver, username, password):
                log.error("Login failed for %s; skipping", portal_key)
                continue

            log.info("Scrapping Started: %s", portal_key)
            log.info("Collecting cookies and token for API access...")
            # Use extract_cookies_and_token to get both cookies (string) and hydra token
            cookie_str, hydra_token = browser_session.extract_cookies_and_token(
                driver, timeout=60
            )
            if not hydra_token:
                log.warning("Hydra token not found! API requests may fail.")
            cookie_map = cookie_string_to_dict(cookie_str)

            log.info("Starting merchant API fetch for portal %s", portal_key)
            merchants, merchant_group_id = fetch_merchants_for_portal(
                cookie_map, hydra_token
            )

            save_raw(
                portal_key,
                {
                    "portal": portal_key,
                    "merchants": merchants,
                    "merchantGroupID": merchant_group_id,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Count statuses
            active_cnt = 0
            restricted_cnt = 0
            inactive_cnt = 0
            for m in merchants:
                status_raw = m.get("status") or ""
                if status_raw == "Yes" or status_raw.lower() == "active":
                    active_cnt += 1
                elif status_raw.lower() == "restricted":
                    restricted_cnt += 1
                elif status_raw == "No" or status_raw.lower() == "inactive":
                    inactive_cnt += 1

            # Prepare Discord notification
            title = "Activity: Grab - Pull Data - Outlet Counter"
            description = (
                f"Objective: Count total outlets per portal and label their status.\n"
                f"Channel: GrabFood\n"
                f"Portal: {portal_key}\n"
                f"Total Tasks: {len(merchants)}\n\n"
                f"📊 Outlet Status:\n"
                f"🟢 Active: {active_cnt}\n"
                f"🟡 Restricted: {restricted_cnt}\n"
                f"🔴 Inactive: {inactive_cnt}"
            )
            # Send notification (using EnvConfig.DISCORD_WEBHOOK_URL via get_discord_webhook_url or direct access if preferred/available)
            # Safe access via EnvConfig
            try:
                webhook_url = EnvConfig.DISCORD_WEBHOOK_URL
                if webhook_url:
                    send_discord_notification(webhook_url, title, description)
                else:
                    log.warning("DISCORD_WEBHOOK_URL not set; skipping notification")
            except Exception as e:
                log.error("Failed to prepare/send Discord notification: %s", e)

            # Map to Monday group
            group_id = None
            for g in settings_grab.MONDAY_TARGET_GROUP:
                if g.get("source_portal") == portal_key:
                    group_id = g.get("group_id")
                    break

            if group_id:
                sync_to_monday(portal_key, group_id, merchants, merchant_group_id)
            else:
                log.warning(
                    "No monday group mapping found for portal %s; skipping monday sync",
                    portal_key,
                )

            # Logout if there are more portals to process
            if i < len(portals) - 1:
                log.info("Logout to Switch to another Portals: %s", portal_key)
                try:
                    driver.get(browser_session.LOGOUT_URL)
                    time.sleep(2)  # Give it a moment to clear session
                except Exception:
                    log.exception("Error during logout for portal %s", portal_key)

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main(headless=False)
