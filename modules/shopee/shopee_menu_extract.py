import time
import pandas as pd
import requests
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from common.monday_utils import get_all_items_from_group
from modules.shopee.browser_session import BrowserSession
from modules.shopee.api_utils import (
    get_shopee_headers,
    get_auth_tokens,
    get_cookies_dict,
)
from common.logger import get_logger
from common.shopee_utils import switch_merchant
from common.notifications import send_discord_file
from common.config import get_config
from config.settings_shopee import MERCHANT_PROCESSING_LIST

from config.settings_menu_extract import (
    MENU_EXTRACT_BOARD_ID,
    MENU_EXTRACT_GROUP_ID,
    MENU_PORTAL_CONFIG,
)

log = get_logger("shopee_menu_extract")

SHOPEE_DISHES_API = "https://foody.shopee.co.id/api/seller/store/dishes"


def format_price(raw_price):
    """
    Convert raw price from Shopee (which often has 5 extra zeros) into a float number.
    E.g., 99999900000 -> 999999.0
    """
    if not raw_price:
        return ""
    try:
        # Shopee raw price usually has 5 extra zeros (1/100000 scale)
        price_val = float(raw_price) / 100000
        return price_val
    except (ValueError, TypeError):
        return raw_price


def fetch_monday_data(target_portal=None):
    """
    Fetch store details from Monday.com.
    If target_portal is provided, only return stores for that portal.
    """
    log.info("Fetching data from Monday.com...")

    # Construct column IDs to fetch
    column_ids = set()
    for config in MENU_PORTAL_CONFIG.values():
        column_ids.add(config["entity_id_col"])
        column_ids.add(config["full_name_col"])
        column_ids.add(config["short_name_col"])

    # Also fetch the color column from Monday (column id: color_mkyfabkn)
    column_ids.add("color_mkyfabkn")
    items = get_all_items_from_group(
        MENU_EXTRACT_BOARD_ID, MENU_EXTRACT_GROUP_ID, list(column_ids)
    )

    if not items:
        log.warning("No items found in Monday board/group.")
        return []

    stores_to_process = []

    for item in items:
        # Create a dictionary for easier column access
        col_vals = {cv["id"]: cv["text"] for cv in item["column_values"]}

        for portal, config in MENU_PORTAL_CONFIG.items():
            # If a specific portal is requested, skip others
            if target_portal and portal != target_portal:
                continue

            entity_id = col_vals.get(config["entity_id_col"], "").strip()

            # Only process if we have a valid Entity ID
            if entity_id:
                store_info = {
                    "portal": portal,
                    "entity_id": entity_id,
                    "full_name": col_vals.get(config["full_name_col"], ""),
                    "short_name": col_vals.get(config["short_name_col"], ""),
                    "color": col_vals.get("color_mkyfabkn", ""),
                }
                stores_to_process.append(store_info)

    log.info(f"Found {len(stores_to_process)} stores to process from Monday.")
    return stores_to_process


def fetch_menu_from_shopee(entity_id, tob_token, base_cookies=None):
    """Fetch menu (dishes) from Shopee API."""
    headers = get_shopee_headers(tob_token, entity_id, base_cookies_dict=base_cookies)

    try:
        response = requests.get(SHOPEE_DISHES_API, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("catalogs", [])
            else:
                log.warning(f"API Error for Entity {entity_id}: {data.get('msg')}")
        else:
            log.warning(f"HTTP Error {response.status_code} for Entity {entity_id}")
    except Exception as e:
        log.error(f"Exception fetching menu for {entity_id}: {e}")

    return []


def process_stores_for_portal(portal_name, stores_list, tob_token, current_cookies):
    """
    Helper function to process a list of stores for a single portal concurrently.
    Returns a list of result rows.
    """
    results = []

    # We can use a thread pool to fetch data in parallel
    # Adjust max_workers as needed (e.g., 5-10 is usually safe for APIs)
    with ThreadPoolExecutor(max_workers=8) as executor:
        # Submit all tasks
        future_to_store = {
            executor.submit(
                fetch_menu_from_shopee, store["entity_id"], tob_token, current_cookies
            ): store
            for store in stores_list
        }

        for future in as_completed(future_to_store):
            store = future_to_store[future]
            entity_id = store["entity_id"]
            full_name = store["full_name"]
            short_name = store["short_name"]
            portal = store["portal"]

            try:
                catalogs = future.result()

                # Process catalogs into rows
                for catalog in catalogs:
                    category_name = catalog.get("name", "Uncategorized")
                    for dish in catalog.get("dishes", []):
                        row = {
                            "Fullname": full_name,
                            "Shortname": short_name,
                            "SID": entity_id,
                            "Category": category_name,
                            "Item": dish.get("name", ""),
                            "Description": dish.get("description", ""),
                            "Fake Price S": format_price(dish.get("list_price", "")),
                            "S Price": format_price(dish.get("price", "")),
                            "Availability": "Yes" if dish.get("available") else "No",
                            "Scale": store.get("color", ""),
                        }
                        results.append(row)

            except Exception as e:
                log.error(f"Error processing store {entity_id} in thread: {e}")

    return results


def extract_menu_for_merchant(browser, portal_name, stores):
    """
    Extracts menu data for a specific merchant/portal.
    Assumes browser is already on the correct merchant or we can get tokens.
    """
    log.info(f"Extracting menu for portal: {portal_name}")

    # Attempt to grab tokens; prefer any cached tokens on the driver
    auth = getattr(browser.driver, "_shopee_auth", None)
    if auth and auth.get("tob_token"):
        tob_token = auth.get("tob_token")
        current_cookies = get_cookies_dict(browser.driver)
    else:
        tob_token, _ = get_auth_tokens(browser.driver)
        current_cookies = get_cookies_dict(browser.driver)

    if not tob_token:
        log.warning(f"No tob_token available for portal {portal_name}. Skipping.")
        return []

    return process_stores_for_portal(portal_name, stores, tob_token, current_cookies)


def save_menu_data(menu_data, filename_suffix=""):
    """
    Saves the extracted menu data to an Excel file.
    """
    if not menu_data:
        log.info("No menu data to save.")
        return

    df = pd.DataFrame(menu_data)

    df.sort_values(by=["SID", "Category", "Item"], inplace=True)

    output_dir = os.path.join(os.getcwd(), "data", "output")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d - %H%M%S")

    suffix = f"_{filename_suffix}" if filename_suffix else ""
    output_file = os.path.join(output_dir, f"ShopeeFood_menu{suffix}_{timestamp}.xlsx")

    # Save to Excel with formatting
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")

        # Apply currency format
        workbook = writer.book
        worksheet = writer.sheets["Sheet1"]

        # Columns to format (checking if they exist in df)
        price_columns = ["Fake Price S", "S Price"]

        for col_name in price_columns:
            if col_name in df.columns:
                col_idx = df.columns.get_loc(col_name) + 1

                for row_idx in range(2, len(df) + 2):
                    cell = worksheet.cell(row=row_idx, column=col_idx)
                    cell.number_format = '"Rp" #,##0'

    log.info(f"Extraction complete. Saved to {output_file}")
    print(f"File saved to: {output_file}")

    # Send to Discord
    try:
        config = get_config()
        if config.DISCORD_WEBHOOK_URL:
            send_discord_file(
                config.DISCORD_WEBHOOK_URL,
                output_file,
                content=f"ShopeeFood Menu Extraction Complete: {os.path.basename(output_file)}",
            )
    except Exception as e:
        log.error(f"Failed to send file to Discord: {e}")


def run_menu_extraction(browser_session, merchant_task):
    """
    Main entry point for main_runner.py.
    Returns the extracted data (list of dicts) instead of saving immediately,
    allowing the runner to aggregate results.
    """
    portal_name = merchant_task["output_name"]
    log.info(f"Starting menu extraction task for: {portal_name}")

    # Fetch Monday data filtered for this portal
    stores = fetch_monday_data(target_portal=portal_name)
    if not stores:
        log.info(f"No stores to process for {portal_name}.")
        return []

    # Extract
    menu_data = extract_menu_for_merchant(browser_session, portal_name, stores)

    return menu_data


def main():
    # Legacy standalone run - processes all portals
    stores = fetch_monday_data()
    if not stores:
        log.info("No stores found to process. Exiting.")
        return

    browser = BrowserSession(headless=True)
    try:
        if not browser.ensure_logged_in():
            log.error("Failed to log in to Shopee. Exiting.")
            return

        # Determine unique portals to process
        # (This logic mimics the old process_stores which iterated over portals)
        all_data = []

        # Group stores by portal
        stores_by_portal = defaultdict(list)
        for store in stores:
            stores_by_portal[store["portal"]].append(store)

        sorted_portals = sorted(stores_by_portal.keys())

        for portal in sorted_portals:
            portal_stores = stores_by_portal[portal]

            # We need to switch merchant if running in this loop
            merchant_info = next(
                (m for m in MERCHANT_PROCESSING_LIST if m["output_name"] == portal),
                None,
            )

            if merchant_info:
                if switch_merchant(browser.driver, browser.wait, merchant_info):
                    log.info(f"Switched to {portal} successfully.")
                    time.sleep(2)
                else:
                    log.error(f"Failed to switch to {portal}. Skipping.")
                    continue

            portal_data = extract_menu_for_merchant(browser, portal, portal_stores)
            all_data.extend(portal_data)

        if all_data:
            save_menu_data(all_data)
        else:
            log.info("No menu data extracted.")

    finally:
        browser.quit()


if __name__ == "__main__":
    main()
