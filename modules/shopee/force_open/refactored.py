"""
Refactored Core Automation Engine for ShopeeFood Auto Open & Auto Close Bot.
Enforces 5-Level System Priority Hierarchy:
1. Status Penangguhan (Suspended => Force OFF)
2. Status Subscription (Expired => Auto Open Disabled)
3. Vercel Toggle (OFF => Force OFF)
4. Jam Operasional (Outside Schedule => Force OFF)
5. ShopeePartner Toggle (Sync Actual Shopee Status with Desired Status)
"""

import os
import sys
import time
import random
import json
import logging
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
while project_root != os.path.dirname(project_root):
    if os.path.exists(os.path.join(project_root, "common")):
        break
    project_root = os.path.dirname(project_root)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.logger import get_logger
from common.notifications import send_discord_notification
from common.data_provider import DataProviderFactory, BaseDataProvider, OutletData
from common.db_manager import DatabaseManager
from modules.shopee.api_utils import get_auth_tokens, get_shopee_headers
from modules.shopee.browser_session import BrowserSession
from modules.shopee.force_open.config_loader import load_config

log = get_logger("force_open")
log.propagate = False

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

SHOPEE_API_BASE = "https://foody.shopee.co.id"
API_TIMEOUT = 5
RATE_LIMIT_DELAY_MIN = 0.3
RATE_LIMIT_DELAY_MAX = 0.7
MAX_PARALLEL_STORES = 1


def process_store_via_api(store_id: str, short_name: str, action: str, tob_token: str, entity_id: str) -> Dict[str, Any]:
    """Executes Store Open or Close action via Shopee TOB API."""
    headers = get_shopee_headers(tob_token, entity_id)

    try:
        if action == "OPEN":
            url = f"{SHOPEE_API_BASE}/api/seller/store/opening-status/action/open"
            log.debug(f"[API_CALL] Executing OPEN for {short_name} (ID: {store_id})")
            response = requests.post(url, json={}, headers=headers, timeout=API_TIMEOUT)
        else:  # CLOSE / PAUSE
            url = f"{SHOPEE_API_BASE}/api/seller/store/opening-status/action/pause"
            log.debug(f"[API_CALL] Executing PAUSE/CLOSE for {short_name} (ID: {store_id})")
            response = requests.post(
                url, json={"close_all_day": True}, headers=headers, timeout=API_TIMEOUT
            )

        data = response.json()
        if data.get("code") == 0:
            log.info(f"[SUCCESS] {action} store success: {short_name} (ID: {store_id})")
            return {"success": True, "action": action}
        else:
            error_msg = data.get("msg", "Unknown API error")
            log.error(f"[API_ERROR] Failed to {action} store {short_name}: {error_msg}")
            return {"success": False, "error": error_msg}

    except requests.exceptions.Timeout:
        log.error(f"[TIMEOUT] API timeout during {action} for {short_name}")
        return {"success": False, "error": "API Timeout"}
    except Exception as e:
        log.error(f"[FAILED] Failed {action} store {short_name}: {e}")
        return {"success": False, "error": str(e)}


def get_store_status_via_api(
    store_long_name: str, tob_token: str, merchant_entity_id: str, target_store_id: str
) -> Dict[str, Any]:
    """Fetches actual display_status from Shopee TOB search API."""
    headers = get_shopee_headers(tob_token, merchant_entity_id)
    clean_store_name = store_long_name.strip()

    payload = {
        "filter": {"store_name": clean_store_name},
        "page_no": 1,
        "page_size": 50,
    }

    display_status_map = {1: "Closed", 2: "Open", 3: "Busy"}

    try:
        url = f"{SHOPEE_API_BASE}/api/seller/stores/search"
        response = requests.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)
        data = response.json()

        if data.get("code") == 0:
            resp_data = data.get("data") or {}
            stores = resp_data.get("store_basic_info_list", [])
            target_store = None

            for store in stores:
                if str(store.get("id")) == str(target_store_id):
                    target_store = store
                    break

            if not target_store and stores:
                target_store = stores[0]

            if target_store:
                display_status = target_store.get("display_status")
                status_name = display_status_map.get(display_status, "Unknown")
                is_open = display_status == 2
                return {
                    "found": True,
                    "display_status": display_status,
                    "display_status_name": status_name,
                    "is_open": is_open,
                    "operating_hours": target_store.get("operating_hours"),
                }
            return {"found": False, "error": "Store not found in search"}
        return {"found": False, "error": data.get("msg", "API Error")}
    except Exception as e:
        return {"found": False, "error": str(e)}


def fetch_store_operating_hours_from_shopee(store_id: str, tob_token: str, merchant_entity_id: str) -> Dict[str, Any]:
    """Fetches store operating hours directly from Shopee Partner API."""
    headers = get_shopee_headers(tob_token, merchant_entity_id)
    url = f"{SHOPEE_API_BASE}/api/seller/store/operating-hours/get"
    payload = {"store_id": int(store_id) if store_id.isdigit() else store_id}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)
        data = response.json()
        if data.get("code") == 0:
            log.info(f"Successfully fetched operating hours from Shopee Partner for Store ID: {store_id}")
            return {"success": True, "operating_hours": data.get("data")}
        else:
            log.warning(f"Failed to fetch operating hours from Shopee Partner for Store ID {store_id}: {data.get('msg')}")
            return {"success": False, "error": data.get("msg")}
    except Exception as e:
        log.error(f"Error fetching operating hours from Shopee Partner for Store ID {store_id}: {e}")
        return {"success": False, "error": str(e)}


import requests  # Import after standard library imports


def run_force_open(
    session=None,
    data_provider: Optional[BaseDataProvider] = None,
    scale_level: Optional[int] = None,
    dry_run: bool = False,
    db_manager: Optional[DatabaseManager] = None
) -> Dict[str, Any]:
    """
    Main entry point for running Auto Open / Auto Close bot cycle.
    Enforces 5-Level Priority Hierarchy for all registered outlets.
    """
    log.info("=" * 80)
    log.info("Starting Auto Open & Auto Close Bot Execution Cycle...")
    log.info("=" * 80)

    if data_provider is None:
        data_provider = DataProviderFactory.create_provider()

    if db_manager is None:
        db_manager = DatabaseManager()

    # 1. Fetch outlets from DataProvider
    outlets = data_provider.fetch_all_outlets()
    log.info(f"Loaded {len(outlets)} outlets from Data Provider.")

    if not outlets:
        log.warning("No outlets found for processing. Exiting cycle.")
        return {}

    stats = {
        "forced_open": [],
        "forced_close": [],
        "already_open": [],
        "already_closed": [],
        "failed": [],
    }

    # 2. Extract Auth Tokens if browser session exists
    tob_token, merchant_entity_id = "", ""
    if session and hasattr(session, "driver") and session.driver:
        tob_token, merchant_entity_id = get_auth_tokens(driver=session.driver)

    for i, outlet in enumerate(outlets):
        log.info(f"\n[{i+1}/{len(outlets)}] Evaluating Outlet: {outlet.outlet_long_name} (ID: {outlet.store_id})")

        # 3. Pull fresh operating hours from Shopee Partner API before evaluation (if authenticated)
        if tob_token:
            try:
                hours_res = fetch_store_operating_hours_from_shopee(
                    outlet.store_id, tob_token, merchant_entity_id or outlet.merchant_id
                )
                if hours_res.get("success") and hours_res.get("operating_hours"):
                    oph = hours_res["operating_hours"]
                    week_hours = oph.get("week_operating_hours", [])
                    if week_hours:
                        today_id = datetime.now().isoweekday()  # 1=Monday ... 7=Sunday
                        today_slot = next((h for h in week_hours if h.get("day") == today_id), None)
                        if not today_slot and week_hours:
                            today_slot = week_hours[0]

                        if today_slot and today_slot.get("time_slots"):
                            slot = today_slot["time_slots"][0]
                            new_open = slot.get("start_time", outlet.open_time)
                            new_close = slot.get("end_time", outlet.close_time)

                            if new_open != outlet.open_time or new_close != outlet.close_time:
                                log.info(f"  -> [SYNC HOURS] Updated fresh operating hours from ShopeePartner: {new_open} - {new_close}")
                                outlet.open_time = new_open
                                outlet.close_time = new_close
                                data_provider.update_outlet(outlet.store_id, {
                                    "open_time": new_open,
                                    "close_time": new_close,
                                    "shopee_operating_hours": oph
                                })
            except Exception as ex:
                log.warning(f"  -> Failed to sync operating hours for {outlet.outlet_short_name}: {ex}")

        # 4. Evaluate 5-Level System Priority Hierarchy
        desired_status, priority_reason = outlet.calculate_desired_shopee_status()
        log.info(f"  -> Priority Decision: Desired Shopee Status = {'OPEN' if desired_status else 'OFF'}")
        log.info(f"  -> Priority Reason: {priority_reason}")

        actual_is_open = None
        shopee_status_name = "Unknown"

        # 5. Check actual status from Shopee if auth token available
        if tob_token:
            status_res = get_store_status_via_api(
                outlet.outlet_long_name, tob_token, merchant_entity_id or outlet.merchant_id, outlet.store_id
            )
            if status_res.get("found"):
                actual_is_open = status_res.get("is_open")
                shopee_status_name = status_res.get("display_status_name")
                log.info(f"  -> Actual Shopee Status: {shopee_status_name}")

        # Default fallback if API search failed or not logged in: assume last recorded status
        if actual_is_open is None:
            actual_is_open = outlet.shopee_toggle_last
            log.info(f"  -> Using last recorded status: {'OPEN' if actual_is_open else 'OFF'}")

        # 5. Execute Action if Actual Status != Desired Status
        bot_action = "NO_ACTION"
        result_status = "SUCCESS"
        error_msg = ""

        if desired_status and not actual_is_open:
            # Auto Open required
            bot_action = "AUTO_OPEN"
            log.info(f"  -> [ACTION REQUIRED] Outlet is OFF, but Priority Engine requires OPEN. Forcing Auto Open...")
            if not dry_run and tob_token:
                res = process_store_via_api(outlet.store_id, outlet.outlet_short_name, "OPEN", tob_token, outlet.store_id)
                if res.get("success"):
                    stats["forced_open"].append(outlet.outlet_short_name)
                    data_provider.update_shopee_status(outlet.store_id, True, "Auto Open Success")
                else:
                    result_status = "FAILED"
                    error_msg = res.get("error", "Unknown error")
                    stats["failed"].append(outlet.outlet_short_name)
            elif dry_run:
                log.info("  -> [DRY_RUN] Would execute Auto Open")
                stats["forced_open"].append(f"{outlet.outlet_short_name} (DRY_RUN)")

        elif not desired_status and actual_is_open:
            # Auto Close required
            bot_action = "AUTO_CLOSE"
            log.info(f"  -> [ACTION REQUIRED] Outlet is OPEN, but Priority Engine requires OFF ({priority_reason}). Forcing Auto Close...")
            if not dry_run and tob_token:
                res = process_store_via_api(outlet.store_id, outlet.outlet_short_name, "CLOSE", tob_token, outlet.store_id)
                if res.get("success"):
                    stats["forced_close"].append(outlet.outlet_short_name)
                    data_provider.update_shopee_status(outlet.store_id, False, "Auto Close Success")
                else:
                    result_status = "FAILED"
                    error_msg = res.get("error", "Unknown error")
                    stats["failed"].append(outlet.outlet_short_name)
            elif dry_run:
                log.info("  -> [DRY_RUN] Would execute Auto Close")
                stats["forced_close"].append(f"{outlet.outlet_short_name} (DRY_RUN)")

        else:
            # Status already matches desired state
            if desired_status:
                stats["already_open"].append(outlet.outlet_short_name)
                log.info("  -> [NO ACTION] Outlet is already OPEN as desired.")
            else:
                stats["already_closed"].append(outlet.outlet_short_name)
                log.info(f"  -> [NO ACTION] Outlet is already OFF as desired ({priority_reason}).")

        # 6. Record Audit Log in SQLite Database
        db_manager.log_action(
            store_id=outlet.store_id,
            outlet_long_name=outlet.outlet_long_name,
            outlet_short_name=outlet.outlet_short_name,
            suspension_status=outlet.is_suspended(),
            subscription_status=outlet.subscription_status,
            vercel_toggle=outlet.vercel_toggle,
            shopee_status_before=actual_is_open,
            bot_action=bot_action,
            shopee_status_after=desired_status if result_status == "SUCCESS" and bot_action != "NO_ACTION" else actual_is_open,
            status_result=result_status,
            error_message=error_msg,
            admin_info=f"Reason: {priority_reason}"
        )

    # 7. Send Notifications if changes/failures occurred
    if (stats["forced_open"] or stats["forced_close"] or stats["failed"]) and DISCORD_WEBHOOK_URL:
        summary_msg = f"**ShopeeFood Bot Execution Cycle Summary** {'[DRY RUN]' if dry_run else ''}\nTotal Outlets: {len(outlets)}"
        fields = [
            {"name": f"✅ Auto Open ({len(stats['forced_open'])})", "value": ", ".join(stats['forced_open']) or "None", "inline": False},
            {"name": f"🛑 Auto Close ({len(stats['forced_close'])})", "value": ", ".join(stats['forced_close']) or "None", "inline": False},
            {"name": f"⚠️ Failures ({len(stats['failed'])})", "value": ", ".join(stats['failed']) or "None", "inline": False},
        ]
        send_discord_notification(
            DISCORD_WEBHOOK_URL,
            "ShopeeFood Bot Status Report",
            summary_msg,
            fields=fields,
            color=5814783 if not stats["failed"] else 15158332
        )

    log.info("Execution Cycle Finished.")
    log.info(f"Summary: Forced Open: {len(stats['forced_open'])}, Forced Close: {len(stats['forced_close'])}, Already Open: {len(stats['already_open'])}, Already Closed: {len(stats['already_closed'])}, Failed: {len(stats['failed'])}")
    return stats
