import json
import time
import os
import sys
import requests
import socket
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def log(level, message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level.upper()}] {message}")


env_path = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path=env_path)

try:
    from grab_scrapper.config.credentials import ACCOUNT_CREDS
except ImportError:
    log("fatal", "`credentials.py` not found.")
    exit()

try:
    from grab_scrapper.config.valsettings import (
        MONDAY_SID_COLUMN_MAP,
        SOURCE_BOARD_ID,
        DESTINATION_BOARD_ID,
    )
except ImportError:
    log("fatal", "`monday_checker/valsettings.py` not found.")
    exit()

try:
    from grab_scrapper.config.settings import (
        SINGLE_OUTLET_CHECK_URL,
        GRAB_MERCHANT_CONFIG,
        TARGET_API_URL,
        MONDAY_TARGET_GROUP,
    )
except ImportError:
    log("fatal", "`grab_scrapper/settings.py` not found.")
    exit()


def is_network_available(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False


from common.monday_api import execute_monday_query
from grab_scrapper.common.session import BrowserSession


def fetch_monday_database(source_portal):
    sid_column = MONDAY_SID_COLUMN_MAP.get(source_portal)
    if not sid_column:
        log(
            "error",
            f"No Store ID column configured for portal '{source_portal}' in settings.",
        )
        return None

    log(
        "info",
        f"Fetching all items from Monday database board for portal '{source_portal}'...",
    )
    all_items = []
    cursor = None

    while True:
        query = f"""
            query ($board_id: [ID!], $cursor: String) {{
                boards(ids: $board_id) {{
                    items_page(limit: 100, cursor: $cursor) {{
                        cursor
                        items {{
                            name
                            column_values(ids: ["{sid_column}"]) {{
                                id
                                text
                            }}
                        }}
                    }}
                }}
            }}
        """
        variables = {"board_id": [str(SOURCE_BOARD_ID)], "cursor": cursor}
        response = execute_monday_query(query, variables)

        if not response or "errors" in response:
            log("error", f"Failed to fetch Monday data: {response.get('errors')}")
            break

        items_page_data = response["data"]["boards"][0]["items_page"]
        items = items_page_data.get("items", [])

        if not items:
            break

        for item in items:
            sid = (
                item["column_values"][0]["text"]
                if item["column_values"] and item["column_values"][0]["text"]
                else ""
            )
            all_items.append({"name": item["name"], "store_id": sid})

        cursor = items_page_data.get("cursor")
        if not cursor:
            break

    log(
        "success",
        f"Fetched a total of {len(all_items)} items from the Monday database.",
    )
    return all_items


def write_to_monday_report(df, account_name):
    target_group_id = next(
        (
            g["group_id"]
            for g in MONDAY_TARGET_GROUP
            if g["source_portal"] == account_name
        ),
        None,
    )
    if not target_group_id:
        log("error", f"No report group_id found for '{account_name}' in settings.")
        return

    # --- Dynamically fetch column IDs for the destination board ---
    log("info", f"Fetching column structure for report board {DESTINATION_BOARD_ID}...")
    query_columns = (
        f"query {{ boards(ids: {DESTINATION_BOARD_ID}) {{ columns {{ id title }} }} }}"
    )
    response_cols = execute_monday_query(query_columns)
    if not response_cols or "data" not in response_cols:
        log(
            "error",
            "Could not fetch report board structure. Check board ID and API key.",
        )
        return

    try:
        column_map = {
            col["title"]: col["id"]
            for col in response_cols["data"]["boards"][0]["columns"]
        }
        # Map titles to the variables that will hold the IDs
        store_id_col = column_map.get("Store ID")
        outlet_status_col = column_map.get("Outlet Status")
        address_status_col = column_map.get("Address Status")
        address_col = column_map.get("Address")
        if not all([store_id_col, outlet_status_col, address_status_col, address_col]):
            log(
                "error",
                "One or more required columns (Store ID, Outlet Status, Address Status, Address) are missing from the report board.",
            )
            return
    except (KeyError, IndexError):
        log("error", "Failed to parse column structure from the report board.")
        return

    log(
        "info",
        f"Fetching existing items from report group '{target_group_id}' to check for 'As is' status...",
    )
    existing_report_items = {}
    query_existing = f"""
        query ($board_id: ID!, $group_id: String!) {{
            boards (ids: [$board_id]) {{
                groups(ids: [$group_id]) {{
                    items_page (limit: 500) {{
                        items {{
                            id
                            state
                            column_values(ids: ["{store_id_col}", "{address_status_col}"]) {{
                                id
                                text
                            }}
                        }}
                    }}
                }}
            }}
        }}
    """
    variables_existing = {"board_id": DESTINATION_BOARD_ID, "group_id": target_group_id}
    response = execute_monday_query(query_existing, variables_existing)
    try:
        items = response["data"]["boards"][0]["groups"][0]["items_page"]["items"]
        # Map by Store ID, as this is the unique key
        for item in items:
            store_id = next(
                (
                    cv["text"]
                    for cv in item["column_values"]
                    if cv["id"] == store_id_col
                ),
                None,
            )
            address_status = next(
                (
                    cv["text"]
                    for cv in item["column_values"]
                    if cv["id"] == address_status_col
                ),
                None,
            )
            if store_id:
                existing_report_items[store_id] = {
                    "id": item["id"],
                    "address_status": address_status,
                    "state": item["state"],
                }
        log(
            "info",
            f"Found {len(existing_report_items)} existing items in the report group.",
        )
    except (KeyError, IndexError, TypeError):
        log(
            "warn",
            "Could not parse existing report items. Will create all items as new.",
        )

    status_map = {
        "ACTIVE": "Active",
        "INACTIVE": "Inactive",
        "RESTRICTED": "Restricted",
    }

    log("info", f"Writing {len(df)} validation results to Monday report board...")
    for index, row in tqdm(
        df.iterrows(), total=df.shape[0], desc=f"Uploading report for {account_name}"
    ):
        store_id = row.get("Store ID")
        existing_item = existing_report_items.get(store_id) if store_id else None

        # Check for "As is" status and skip if found (your intentional logic)
        if existing_item and existing_item.get("address_status") == "As is":
            log(
                "info",
                f"Skipping update for Store ID '{store_id}' because its status is 'As is'.",
            )
            continue

        # *** MODIFIED LOGIC HERE ***
        # Only skip items that are explicitly 'deleted' (in the trash)
        if existing_item and existing_item.get("state") == "deleted":
            log(
                "warn",
                f"Skipping update for Store ID '{store_id}' (Monday ID: {existing_item['id']}) because it is 'deleted' on Monday.com and cannot be updated.",
            )
            continue

        item_name = row.get("Name")
        if not item_name or pd.isna(item_name):
            item_name = f"Outlet - {row.get('Store ID', 'Unknown ID')}"

        mapped_status = status_map.get(row["Outlet Status"], row["Outlet Status"])

        column_values = {
            "name": item_name,
            store_id_col: row["Store ID"],
            outlet_status_col: {"label": mapped_status},
            address_status_col: {"label": row["Address Status"]},
            address_col: row["Address"],
        }
        column_values = {
            k: v
            for k, v in column_values.items()
            if (isinstance(v, dict) or (v and pd.notna(v)))
        }

        if existing_item:
            # UPDATE existing item
            query = """
                mutation ($item_id: ID!, $board_id: ID!, $column_values: JSON!) {
                    change_multiple_column_values(item_id: $item_id, board_id: $board_id, column_values: $column_values) { id }
                }
            """
            variables = {
                "item_id": existing_item["id"],
                "board_id": DESTINATION_BOARD_ID,
                "column_values": json.dumps(column_values),
            }
        else:
            # CREATE new item
            query = """
                mutation ($item_name: String!, $board_id: ID!, $group_id: String!, $column_values: JSON!) {
                    create_item (board_id: $board_id, group_id: $group_id, item_name: $item_name, column_values: $column_values) { id }
                }
            """
            variables = {
                "item_name": item_name,
                "board_id": DESTINATION_BOARD_ID,
                "group_id": target_group_id,
                "column_values": json.dumps(column_values),
            }

        while True:
            response_data = execute_monday_query(query, variables)
            if response_data is None:
                log(
                    "warn",
                    "API call failed due to a network error. Pausing until connection is restored...",
                )
                while not is_network_available():
                    log(
                        "error",
                        "Network connection is down. Re-checking in 30 seconds...",
                    )
                    time.sleep(30)
                log("success", "Network connection restored. Retrying the failed item.")
                continue
            if "errors" in response_data:
                log(
                    "error",
                    f"Monday API returned a permanent error for item '{item_name}': {response_data['errors']}. Skipping this item.",
                )
                break
            break
        time.sleep(0.5)


def collect_all_merchants(driver):
    """
    Navigates to the menu page and intercepts API calls to extract merchant data.
    This function now handles navigation to ensure requests are not missed.
    """
    log("info", "Navigating to menu page to start data collection...")
    del driver.requests
    driver.get(GRAB_MERCHANT_CONFIG["merchant_list_url"])

    try:
        log("info", "Attempting to capture the main multi-outlet API (timeout: 30s)...")
        request = driver.wait_for_request(TARGET_API_URL, timeout=20)

        log("info", "Main search API was called. Proceeding with full data collection.")
        data = json.loads(request.response.body.decode("utf-8"))
        merchants_batch = data.get("merchants", [])
        has_more_data = data.get("hasMore", False)
        all_merchants = merchants_batch

        if not has_more_data:
            return all_merchants, "MULTI_OUTLET"

        scrollable_element = driver.find_element(By.CSS_SELECTOR, "div.dui-table-body")
        page_scroll_attempts = 0
        while has_more_data:
            previous_merchant_count = len(all_merchants)
            del driver.requests
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_element
            )
            try:
                scroll_request = driver.wait_for_request(TARGET_API_URL, timeout=60)
                if scroll_request and scroll_request.response:
                    data = json.loads(scroll_request.response.body.decode("utf-8"))
                    merchants_batch = data.get("merchants", [])
                    if merchants_batch:
                        all_merchants.extend(merchants_batch)
                    if len(all_merchants) == previous_merchant_count:
                        page_scroll_attempts += 1
                        if page_scroll_attempts > 2:
                            log(
                                "error",
                                "No new merchants after multiple scroll attempts. Forcing stop.",
                            )
                            break
                    else:
                        page_scroll_attempts = 0
                    has_more_data = data.get("hasMore", False)
            except (json.JSONDecodeError, TimeoutException):
                log("warn", "Timed out while scrolling. Assuming no more data.")
                break
        return all_merchants, "MULTI_OUTLET"
    except TimeoutException:
        log(
            "info",
            "Main API not found. Checking for the single-outlet portal API (timeout: 20s)...",
        )
        try:
            request = driver.wait_for_request(SINGLE_OUTLET_CHECK_URL, timeout=20)
            log("info", "Portal API was called, indicating a single-outlet account.")
            if request and request.response:
                data = json.loads(request.response.body.decode("utf-8"))
                return data.get("merchants", []), "SINGLE_OUTLET"
            else:
                return [], "ERROR"
        except TimeoutException:
            log(
                "error",
                "Did not capture any merchant data API call within the timeout period.",
            )
            return [], "ERROR"
    except (json.JSONDecodeError, NoSuchElementException, Exception) as e:
        log("error", f"An error occurred during data collection: {e}")
        return [], "ERROR"


def format_single_outlet_for_report(grab_data):
    if not grab_data:
        return pd.DataFrame()
    merchant = grab_data[0]
    report_data = {
        "Name": merchant.get("merchantName"),
        "Store ID": merchant.get("merchantID"),
        "Outlet Status": merchant.get("status"),
        "Address Status": "",
        "Address": merchant.get("address"),
    }
    return pd.DataFrame([report_data])


def perform_validation(monday_data, grab_data):
    log("info", "Performing validation...")

    status_map = {
        "ACTIVE": "Active",
        "INACTIVE": "Inactive",
    }

    results = []
    grab_data_dict = {item["merchantID"]: item for item in grab_data}
    for monday_item in tqdm(monday_data, desc="Validating outlets"):
        store_id = monday_item["store_id"]

        if not store_id:
            result_row = {
                "Name": monday_item["name"],
                "Store ID": "",
                "Outlet Status": "",
                "Address Status": "False",
                "Address": "Skipped - Missing Store ID in Database",
            }
            results.append(result_row)
            continue

        grab_record = grab_data_dict.get(store_id)
        result_row = {
            "Name": monday_item["name"],
            "Store ID": store_id,
            "Outlet Status": "",
            "Address Status": "False",
            "Address": "",
        }

        if grab_record:
            raw_status = grab_record.get("status", "")
            result_row["Outlet Status"] = status_map.get(raw_status, raw_status)
            grab_address = grab_record.get("address", "").lower()
            monday_name = monday_item.get("name", "").lower()
            if monday_name and monday_name in grab_address:
                result_row["Address Status"] = "True"
                result_row["Address"] = grab_record.get("address", "")
            else:
                result_row["Address Status"] = "Warning"
                result_row["Address"] = grab_record.get("address", "")
        results.append(result_row)
    return pd.DataFrame(results)


if __name__ == "__main__":
    print("=" * 50)
    print("=== Grab vs Monday Address Validator ===")
    print("=" * 50)
    browser = BrowserSession(GRAB_MERCHANT_CONFIG)
    if not browser.driver:
        exit()
    while True:
        account_list = list(ACCOUNT_CREDS.keys())
        print("\n" + "=" * 70)
        log("info", "Please select an option:")
        print("   1. Run All Accounts")
        for i, name in enumerate(account_list):
            print(f"   {i+2}. {name}")
        print(f"   {len(account_list) + 2}. Exit")
        print("=" * 70)
        try:
            choice = int(input(f"Enter number (1-{len(account_list) + 2}): "))
        except ValueError:
            log("error", "Invalid input.")
            continue
        accounts_to_process = []
        if choice == 1:
            accounts_to_process = account_list
        elif 2 <= choice <= len(account_list) + 1:
            accounts_to_process.append(account_list[choice - 2])
        elif choice == len(account_list) + 2:
            break
        else:
            log("error", f"Invalid choice.")
            continue

        for account_name in accounts_to_process:
            print("-" * 70)
            log("info", f"--- Starting validation for account: {account_name} ---")

            if not browser.login(account_name, ACCOUNT_CREDS[account_name]):
                log("error", f"Login failed for {account_name}. Skipping.")
                continue

            grab_live_data, api_type = collect_all_merchants(browser.driver)

            if api_type == "ERROR" or not grab_live_data:
                log(
                    "warn",
                    f"Could not extract data from Grab for {account_name}. Creating 'False' report for database items.",
                )
                monday_db_data = fetch_monday_database(account_name)
                if monday_db_data:
                    report_df = perform_validation(monday_db_data, [])
                    if not report_df.empty:
                        write_to_monday_report(report_df, account_name)
                        log(
                            "success",
                            f"Wrote 'False' report for {account_name} to Monday.com.",
                        )
                else:
                    log(
                        "warn",
                        f"No data in Monday DB for {account_name}, nothing to report.",
                    )
                continue

            report_df = pd.DataFrame()
            if api_type == "SINGLE_OUTLET":
                log(
                    "info",
                    "Single-outlet account detected. Formatting raw data for report.",
                )
                report_df = format_single_outlet_for_report(grab_live_data)
            elif api_type == "MULTI_OUTLET":
                log(
                    "info",
                    "Multi-outlet account detected. Proceeding with full validation.",
                )
                monday_db_data = fetch_monday_database(account_name)
                if not monday_db_data:
                    log(
                        "warn",
                        f"No data in Monday database for {account_name}. Skipping validation.",
                    )
                    continue
                report_df = perform_validation(monday_db_data, grab_live_data)
            else:
                report_df = pd.DataFrame()

            if not report_df.empty:
                write_to_monday_report(report_df, account_name)
                log("success", f"Report for {account_name} written to Monday.com.")
            else:
                log("warn", "Process produced an empty report. Nothing to write.")

        log("info", "Batch finished. Returning to main menu.")

    browser.quit()
    log("info", "Process finished.")
