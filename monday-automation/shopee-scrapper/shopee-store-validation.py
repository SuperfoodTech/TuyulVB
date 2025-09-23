import pandas as pd
from services.base.service_factory import ServiceFactory
from services.utils.logging import setup_logging
from services.utils.data_transformer import restructure_data_from_google_sheet
import logging
from services.config import GOOGLE_SHEET_NAME, INPUT_WORKSHEET_NAME, COLUMN_MAPPING

# --- Logging Function ---
setup_logging()
log = logging.getLogger(__name__)


def perform_validation(portal_data, tasks_to_validate):
    log.info(f"Performing validation for {len(tasks_to_validate)} tasks...")
    results = []
    portal_dict = {str(store['id']): store for store in portal_data}

    for task in tasks_to_validate:
        store_id = task['store_id']
        portal_record = portal_dict.get(store_id)

        name_result = "Not Found"
        actual_name = ""

        if portal_record:
            actual_name = portal_record.get('name', '').strip()
            if task['ofd_name'].lower() == actual_name.lower():
                name_result = "Match"
            else:
                name_result = "Mismatch"

        results.append({
            'Source Portal': task['source_portal'],
            'Outlet Name': task['outlet_name'],
            'Store ID': store_id,
            'Outlet Name (OFD)': task['ofd_name'],
            'Actual Name': actual_name,
            'Name Result': name_result,
            'Name Status(Blank)': "",
            'Actual Outlet Name': actual_name,
            'Address Result': "",
            'Address Status(Blank)': "",
            'Actual Address': portal_record.get('address', '') if portal_record else ""
        })

    log.info("Validation complete.")
    return pd.DataFrame(results)


# --- Main Execution ---
if __name__ == "__main__":
    gsheet_client = ServiceFactory.get_sheets_client()
    shopee_scraper = ServiceFactory.get_shopee_scraper()

    input_df = gsheet_client.read_worksheet_as_dataframe(
        GOOGLE_SHEET_NAME, INPUT_WORKSHEET_NAME)
    if input_df is None:
        log.error("Could not read input data from Google Sheet. Exiting.")
        if shopee_scraper:
            shopee_scraper.quit()
        exit()

    all_tasks = restructure_data_from_google_sheet(input_df, COLUMN_MAPPING)
    if not all_tasks:
        log.error("No tasks were created from the input data. Exiting.")
        if shopee_scraper:
            shopee_scraper.quit()
        exit()

    if not shopee_scraper or not shopee_scraper.driver:
        log.fatal("Browser session failed to initialize. Exiting.")
        exit()

    try:
        while True:
            account_list = list(shopee_scraper.credentials.keys())
            print("\n" + "="*70)
            log.info("Please select an option:")
            print("  1. Run All Accounts")
            for i, name in enumerate(account_list):
                print(f"  {i+2}. {name}")
            print(f"  {len(account_list) + 2}. Exit")
            print("="*70)

            try:
                choice = int(
                    input(f"Enter number (1-{len(account_list) + 2}): "))
            except ValueError:
                log.error("Invalid input.")
                continue

            if choice == len(account_list) + 2:
                break

            accounts_to_process = []
            if choice == 1:
                accounts_to_process = account_list
            elif 2 <= choice <= len(account_list) + 1:
                accounts_to_process.append(account_list[choice - 2])
            else:
                log.error("Invalid choice.")
                continue

            for account_name in accounts_to_process:
                print("-" * 70)
                log.info(
                    f"--- Starting processing for account: {account_name} ---")

                tasks_for_account = [
                    t for t in all_tasks if t['source_portal'] == account_name]
                if not tasks_for_account:
                    log.warn(
                        f"No tasks found for account '{account_name}'. Skipping.")
                    continue

                if shopee_scraper.login(account_name):
                    store_data = shopee_scraper.collect_data()
                    if store_data:
                        report_df = perform_validation(
                            store_data, tasks_for_account)
                        gsheet_client.write_dataframe_to_worksheet(report_df,
                                                                   GOOGLE_SHEET_NAME, f"Report_{account_name}")
                    else:
                        log.error(
                            f"No store data collected for {account_name}. Cannot generate report.")
                else:
                    log.warn(
                        f"Login failed for account '{account_name}'. Skipping.")
    finally:
        if shopee_scraper:
            shopee_scraper.quit()
        log.info("Process finished.")
