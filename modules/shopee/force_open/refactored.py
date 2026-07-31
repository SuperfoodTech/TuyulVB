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

SHOPEE_API_BASE = "https://api.partner.shopee.co.id/nb/mss"
SHOPEE_API_BASE_LEGACY = "https://foody.shopee.co.id"  # kept for backward compat
API_TIMEOUT = 10
RATE_LIMIT_DELAY_MIN = 0.3
RATE_LIMIT_DELAY_MAX = 0.7
MAX_PARALLEL_STORES = 1


def process_store_via_api(
    store_id: str, short_name: str, action: str, tob_token: str, entity_id: str,
    driver = None
) -> Dict[str, Any]:
    """Executes Store Open or Close action via Shopee Partner API with Selenium fallback."""
    headers = get_shopee_headers(tob_token, entity_id)

    parsed_store_id = int(store_id) if str(store_id).isdigit() else store_id
    try:
        if action == "OPEN":
            url = f"{SHOPEE_API_BASE}/web-api/FoodOperationServer/SetStoreOpeningStatus"
            payload = {"store_id": parsed_store_id, "status": 1}  # 1 = Open
            log.debug(f"[API_CALL] Executing OPEN for {short_name} (ID: {store_id})")
            response = requests.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)
        else:  # CLOSE / PAUSE
            url = f"{SHOPEE_API_BASE}/web-api/FoodOperationServer/SetStoreOpeningStatus"
            payload = {"store_id": parsed_store_id, "status": 0}  # 0 = Close
            log.debug(f"[API_CALL] Executing PAUSE/CLOSE for {short_name} (ID: {store_id})")
            response = requests.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)

        data = response.json()
        if data.get("error_code") == 0 or data.get("code") == 0 or data.get("errorCode") == 0:
            log.info(f"[SUCCESS] {action} store success: {short_name} (ID: {store_id})")
            return {"success": True, "action": action}
        else:
            error_msg = data.get("error_msg") or data.get("errorMsg") or data.get("msg", "Unknown API error")
            log.warning(f"[API_NOTICE] API {action} response for {short_name}: {error_msg}")
            # Try legacy endpoint first, then Selenium UI fallback
            leg_res = _process_store_legacy(store_id, short_name, action, tob_token, entity_id)
            if leg_res.get("success"):
                return leg_res
            if driver:
                return _process_store_via_selenium(driver, store_id, short_name, action)
            return leg_res

    except Exception as e:
        log.warning(f"[API_EXCEPTION] {action} store {short_name}: {e}")
        if driver:
            return _process_store_via_selenium(driver, store_id, short_name, action)
        return {"success": False, "error": str(e)}


def _process_store_legacy(store_id: str, short_name: str, action: str, tob_token: str, entity_id: str) -> Dict[str, Any]:
    """Fallback: Executes Store Open or Close via legacy foody.shopee.co.id API."""
    headers = get_shopee_headers(tob_token, entity_id)
    parsed_store_id = int(store_id) if str(store_id).isdigit() else store_id
    try:
        if action == "OPEN":
            url = f"{SHOPEE_API_BASE_LEGACY}/api/seller/store/opening-status/action/open"
            response = requests.post(url, json={"store_id": parsed_store_id}, headers=headers, timeout=API_TIMEOUT)
        else:
            url = f"{SHOPEE_API_BASE_LEGACY}/api/seller/store/opening-status/action/pause"
            payload = {"close_all_day": True, "pause_duration": -1, "store_id": parsed_store_id}
            response = requests.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)
        data = response.json()
        if data.get("code") == 0:
            log.info(f"[LEGACY SUCCESS] {action} store: {short_name} (ID: {store_id})")
            return {"success": True, "action": action}
        error_msg = data.get("msg", "Unknown legacy API error")
        return {"success": False, "error": error_msg}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _process_store_via_selenium(driver, store_id: str, short_name: str, action: str) -> Dict[str, Any]:
    """Fallback 2: Performs store Open or Close via Selenium UI interaction."""
    if not driver:
        return {"success": False, "error": "No Selenium driver available"}
    try:
        log.info(f"🌐 [SELENIUM FALLBACK] Attempting {action} for {short_name} via browser UI...")
        driver.get("https://partner.shopee.co.id/food/dashboard")
        time.sleep(3)
        # Search for toggle switch elements on page
        toggles = driver.find_elements("xpath", "//button[contains(@class, 'switch') or contains(@class, 'toggle')] | //input[@type='checkbox']")
        if toggles:
            for tog in toggles:
                try:
                    tog.click()
                    time.sleep(2)
                    log.info(f"✅ [SELENIUM SUCCESS] Clicked toggle for {short_name}")
                    return {"success": True, "action": action, "via": "selenium"}
                except Exception:
                    pass
        log.warning(f"⚠️ [SELENIUM UI] Toggle element not found on page for {short_name}")
        return {"success": False, "error": "Selenium UI toggle not found"}
    except Exception as ex:
        log.error(f"❌ [SELENIUM ERROR] Browser interaction failed: {ex}")
        return {"success": False, "error": str(ex)}



def get_store_status_via_api(
    store_long_name: str, tob_token: str, merchant_entity_id: str, target_store_id: str,
    prefetched_map: dict = None
) -> Dict[str, Any]:
    """Fetches actual display_status from Shopee Partner API."""
    if prefetched_map:
        sid = str(target_store_id)
        sname = store_long_name.strip().lower()
        info = prefetched_map.get(sid) or prefetched_map.get(sname)
        if not info:
            for k, v in prefetched_map.items():
                if k and len(k) > 3 and (k in sname or sname in k):
                    info = v
                    break
        if info:
            return {
                "found": True,
                "display_status": info.get("status_code", 1),
                "display_status_name": info.get("status_name", "Open"),
                "is_open": info.get("is_open", True),
            }

    headers = get_shopee_headers(tob_token, merchant_entity_id)

    display_status_map = {0: "Closed", 1: "Open", 2: "Busy", 3: "Closed"}  # new API codes
    display_status_map_legacy = {1: "Closed", 2: "Open", 3: "Busy"}

    # Try PartnerServer/GetStoreList
    try:
        url = f"{SHOPEE_API_BASE}/web-api/PartnerServer/GetStoreList"
        resp = requests.post(url, json={}, headers=headers, timeout=API_TIMEOUT)
        data = resp.json()
        if data.get("errorCode") == 0 or data.get("code") == 0:
            stores = (data.get("data") or {}).get("list", [])
            sid = str(target_store_id)
            sname = store_long_name.strip().lower()
            target_store = next((s for s in stores if str(s.get("storeId") or s.get("store_id")) == sid), None)
            if not target_store:
                target_store = next((s for s in stores if (s.get("storeName") or "").strip().lower() == sname), None)
            if target_store:
                st_code = target_store.get("status", 1)
                is_open = st_code == 1
                status_name = "Open" if is_open else "Closed"
                return {"found": True, "display_status": st_code, "display_status_name": status_name, "is_open": is_open}
    except Exception:
        pass

    # Fallback: Legacy foody.shopee.co.id stores/search
    clean_store_name = store_long_name.strip()
    payload = {"filter": {"store_name": clean_store_name}, "page_no": 1, "page_size": 50}
    try:
        url = f"{SHOPEE_API_BASE_LEGACY}/api/seller/stores/search"
        response = requests.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)
        data = response.json()
        if data.get("code") == 0:
            stores = (data.get("data") or {}).get("store_basic_info_list", [])
            target_store = next((s for s in stores if str(s.get("id")) == str(target_store_id)), None)
            if not target_store and stores:
                target_store = stores[0]
            if target_store:
                display_status = target_store.get("display_status")
                status_name = display_status_map_legacy.get(display_status, "Unknown")
                is_open = display_status == 2
                return {"found": True, "display_status": display_status, "display_status_name": status_name, "is_open": is_open, "operating_hours": target_store.get("operating_hours")}
            return {"found": False, "error": "Store not found"}
        return {"found": False, "error": data.get("msg", "API Error")}
    except Exception as e:
        return {"found": False, "error": str(e)}


def fetch_store_operating_hours_from_shopee(store_id: str, tob_token: str, merchant_entity_id: str) -> Dict[str, Any]:
    """Fetches store operating hours from Shopee Partner API (new + legacy fallback)."""
    headers = get_shopee_headers(tob_token, merchant_entity_id)
    parsed_id = int(store_id) if str(store_id).isdigit() else store_id

    def _safe_json(resp) -> dict:
        """Parse response JSON safely — return {} if not a dict (e.g. API returns `true`)."""
        try:
            data = resp.json()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    # Try new API
    try:
        url = f"{SHOPEE_API_BASE}/web-api/FoodOperationServer/GetStoreOperatingHours"
        response = requests.post(url, json={"store_id": parsed_id}, headers=headers, timeout=API_TIMEOUT)
        data = _safe_json(response)
        if data.get("error_code") == 0:
            log.info(f"Successfully fetched operating hours (new API) for Store ID: {store_id}")
            return {"success": True, "operating_hours": data.get("data")}
    except Exception:
        pass

    # Fallback: legacy API
    try:
        url_legacy = f"{SHOPEE_API_BASE_LEGACY}/api/seller/store/operating-hours/get"
        response = requests.post(url_legacy, json={"store_id": parsed_id}, headers=headers, timeout=API_TIMEOUT)
        data = _safe_json(response)
        if data.get("code") == 0:
            log.info(f"Successfully fetched operating hours (legacy API) for Store ID: {store_id}")
            return {"success": True, "operating_hours": data.get("data")}
        else:
            log.debug(f"Operating hours API call returned non-standard status for Store ID {store_id}")
            return {"success": False, "error": "API unavailable"}
    except Exception as e:
        log.debug(f"Operating hours API error for Store ID {store_id}: {e}")
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

    # 2. Extract Auth Tokens if browser session exists or from cache fallback
    tob_token, merchant_entity_id = "", ""
    if session and hasattr(session, "driver") and session.driver:
        tob_token, merchant_entity_id = get_auth_tokens(driver=session.driver)

    if not tob_token:
        # Fallback to cached token file if available
        cache_file = os.path.join(project_root, "data", "cache", "shopee_auth_tokens.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    cache_data = json.load(f)
                    tob_token = cache_data.get("shopee_tob_token", "")
                    merchant_entity_id = cache_data.get("shopee_tob_entity_id", "")
                    if tob_token:
                        log.info("  -> Loaded active Shopee authentication tokens from local cache.")
            except Exception as ex:
                log.warning(f"  -> Could not load token cache: {ex}")

    if not tob_token:
        log.warning("⚠️ [AUTH NOTICE] shopee_tob_token tidak ditemukan. Silakan login ke Shopee Partner via CLI/Browser agar bot dapat mengeksekusi buka/tutup toko di API Shopee.")
    else:
        # Update local cache for future background calls
        cache_dir = os.path.join(project_root, "data", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, "shopee_auth_tokens.json")
        try:
            with open(cache_file, "w") as f:
                json.dump({"shopee_tob_token": tob_token, "shopee_tob_entity_id": merchant_entity_id, "updated_at": datetime.now().isoformat()}, f)
        except Exception:
            pass

    # 2. Pre-fetch real-time store status map via PartnerServer/GetStoreList
    prefetched_status_map = {}
    if tob_token:
        try:
            url_list = f"{SHOPEE_API_BASE}/web-api/PartnerServer/GetStoreList"
            hdr = get_shopee_headers(tob_token, merchant_entity_id)
            r_list = requests.post(url_list, json={}, headers=hdr, timeout=API_TIMEOUT)
            d_list = r_list.json()
            if d_list.get("errorCode") == 0 or d_list.get("code") == 0:
                s_items = (d_list.get("data") or {}).get("list", [])
                for s_item in s_items:
                    sid = str(s_item.get("storeId") or s_item.get("store_id") or "")
                    sname = (s_item.get("storeName") or s_item.get("store_name") or "").strip().lower()
                    st_code = s_item.get("status")
                    is_op = (st_code == 1)
                    st_label = "Open" if is_op else "Closed"
                    entry = {"is_open": is_op, "status_name": st_label, "status_code": st_code}
                    if sid:
                        prefetched_status_map[sid] = entry
                    if sname:
                        prefetched_status_map[sname] = entry
                log.info(f"✅ Pre-fetched real-time status for {len(s_items)} stores from Shopee Partner API.")
        except Exception as ex_list:
            log.warning(f"Could not pre-fetch store list from Shopee Partner API: {ex_list}")

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
                        DAY_NAME_MAP = {1: "Senin", 2: "Selasa", 3: "Rabu", 4: "Kamis", 5: "Jumat", 6: "Sabtu", 7: "Minggu"}
                        day_hours_dict = {}
                        for day_idx in range(1, 8):
                            day_name = DAY_NAME_MAP[day_idx]
                            slot_info = next((h for h in week_hours if h.get("day") == day_idx), None)
                            if slot_info and slot_info.get("time_slots"):
                                ts = slot_info["time_slots"][0]
                                st = ts.get("start_time", "")
                                et = ts.get("end_time", "")
                                day_hours_dict[day_name] = f"{st}-{et}" if st and et else "Tutup"
                            else:
                                day_hours_dict[day_name] = "Tutup"

                        today_id = datetime.now().isoweekday()  # 1=Monday ... 7=Sunday
                        today_slot = next((h for h in week_hours if h.get("day") == today_id), None)
                        if not today_slot and week_hours:
                            today_slot = week_hours[0]

                        if today_slot and today_slot.get("time_slots"):
                            slot = today_slot["time_slots"][0]
                            new_open = slot.get("start_time", outlet.open_time)
                            new_close = slot.get("end_time", outlet.close_time)

                            outlet.open_time = new_open
                            outlet.close_time = new_close
                            data_provider.update_outlet(outlet.store_id, {
                                "open_time": new_open,
                                "close_time": new_close,
                                "shopee_operating_hours": oph,
                                "day_operating_hours": day_hours_dict
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
        if tob_token or prefetched_status_map:
            status_res = get_store_status_via_api(
                outlet.outlet_long_name, tob_token, merchant_entity_id or outlet.merchant_id, outlet.store_id,
                prefetched_map=prefetched_status_map
            )
            if status_res.get("found"):
                actual_is_open = status_res.get("is_open")
                shopee_status_name = status_res.get("display_status_name")
                log.info(f"  -> Actual Shopee Status: {shopee_status_name}")
                # Sync actual status to DataProvider & Google Sheets Column P
                data_provider.update_shopee_status(outlet.store_id, actual_is_open, f"Shopee Status: {shopee_status_name}")

        # Default fallback if API search failed or not logged in: assume last recorded status
        if actual_is_open is None:
            actual_is_open = outlet.shopee_toggle_last
            log.info(f"  -> Using last recorded status: {'OPEN' if actual_is_open else 'OFF'}")

        # ALWAYS sync actual status & 7-day operating hours to DataProvider & Google Sheets (Kolom P & Kolom S-Y)
        shopee_label = shopee_status_name if shopee_status_name != "Unknown" else ("OPEN" if actual_is_open else "OFF")
        data_provider.update_shopee_status(outlet.store_id, actual_is_open, f"Shopee Status: {shopee_label}")

        # Dynamic 7-day operating hours dictionary (from Google Sheet or Shopee API)
        sheet_day_dict = (outlet.raw_extra or {}).get("day_operating_hours")
        if not sheet_day_dict:
            single_hours = f"{outlet.open_time}-{outlet.close_time}" if outlet.open_time and outlet.close_time else "Tutup"
            sheet_day_dict = {day: single_hours for day in ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]}
        day_dict = getattr(outlet, "day_operating_hours", None) or sheet_day_dict
        data_provider.update_outlet(outlet.store_id, {"day_operating_hours": day_dict, "shopee_toggle_last": actual_is_open})


        # 5. Execute Action if Actual Status != Desired Status
        bot_action = "NO_ACTION"
        result_status = "SUCCESS"
        error_msg = ""

        if desired_status and not actual_is_open:
            # Auto Open required
            bot_action = "AUTO_OPEN"
            log.info(f"  -> [ACTION REQUIRED] Outlet is OFF, but Priority Engine requires OPEN. Forcing Auto Open...")
            driver_obj = session.driver if session and hasattr(session, "driver") else None
            if not dry_run and (tob_token or driver_obj):
                res = process_store_via_api(outlet.store_id, outlet.outlet_short_name, "OPEN", tob_token, outlet.store_id, driver=driver_obj)
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
            driver_obj = session.driver if session and hasattr(session, "driver") else None
            if not dry_run and (tob_token or driver_obj):
                res = process_store_via_api(outlet.store_id, outlet.outlet_short_name, "CLOSE", tob_token, outlet.store_id, driver=driver_obj)
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
