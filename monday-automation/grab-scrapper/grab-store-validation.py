import pandas as pd
from tqdm import tqdm

from services.base.service_factory import ServiceFactory
from services.utils.logging import setup_logging
import logging
from services.config import COLUMN_MAPPING, GOOGLE_SHEET_NAME, INPUT_WORKSHEET_NAME

# --- Logging Function ---
setup_logging()
log = logging.getLogger(__name__)

# --- Data Collection and Validation ---


def restructure_data(df):
    tasks = []
    log.info("🛠️ Restructuring data...")

    all_required_cols = set()
    for mapping in COLUMN_MAPPING:
        all_required_cols.update([
            mapping["outlet_name"],
            mapping["ofd_name_col"],
            mapping["id_col"]
        ])

    if not all_required_cols.issubset(df.columns):
        missing_cols = all_required_cols - set(df.columns)
        log.error(
            f"The following required columns are missing from your sheet: {', '.join(missing_cols)}")
        return []

    for index, row in df.iterrows():
        for mapping in COLUMN_MAPPING:
            ofd_name = row.get(mapping["ofd_name_col"])

            if pd.notna(ofd_name) and str(ofd_name).strip() != "":
                store_id_raw = row.get(mapping["id_col"])

                tasks.append({
                    "outlet_name": str(row.get(mapping["outlet_name"], "")).strip(),
                    "ofd_name": str(ofd_name).strip(),
                    "store_id": str(store_id_raw).strip() if pd.notna(store_id_raw) else "",
                    "source_portal": mapping["source_portal"],
                })
    return tasks


def create_single_outlet_report(tasks_for_account):
    """Creates a DataFrame where all results are False for a single-outlet account."""
    log.info("Generating a report for single-outlet account...")
    results = []
    for task in tasks_for_account:
        results.append({
            'Outlet Name': task['outlet_name'],
            'Outlet Name (OFD)': task['ofd_name'],
            'Store ID': task['store_id'],
            'Name Result': 'False',
            'Name Status (Blank)': '',
            'Actual Outlet Name': '',
            'Address Result': 'False',
            'Address Status (Blank)': '',
            'Actual Address': '',
            'Status': '',
            'Integration Status': ''
        })
    return pd.DataFrame(results)


def perform_validation(portal_data_df, tasks_to_validate):
    log.info(
        f"Performing validation logic for {len(tasks_to_validate)} tasks...")
    results = []
    if 'merchantID' in portal_data_df.columns:
        portal_data_df['merchantID'] = portal_data_df['merchantID'].astype(str)

    portal_dict = portal_data_df.set_index('merchantID').to_dict('index')

    for task in tqdm(tasks_to_validate, desc="Validating Merchants"):
        merchant_id = task['store_id']
        outlet_name_sheet = task['outlet_name']
        ofd_name_sheet = task['ofd_name']

        output_row = {
            'Outlet Name': outlet_name_sheet,
            'Outlet Name (OFD)': ofd_name_sheet,
            'Store ID': merchant_id,
            'Name Result': 'N/A',
            'Name Status (Blank)': '',
            'Actual Outlet Name': '',
            'Address Result': 'N/A',
            'Address Status (Blank)': '',
            'Actual Address': '',
            'Status': '',
            'Integration Status': ''
        }

        if not merchant_id:
            output_row['Status'] = 'Skipped - Missing Store ID'
            results.append(output_row)
            continue

        portal_record = portal_dict.get(merchant_id)

        if portal_record:
            name_portal = str(portal_record.get('merchantName', '')).strip()
            output_row['Actual Outlet Name'] = name_portal
            if not ofd_name_sheet:
                output_row['Name Result'] = 'False'
                output_row['Status'] = 'Skipped - Missing OFD Name'
            elif ofd_name_sheet.lower() == name_portal.lower():
                output_row['Name Result'] = 'True'
                output_row['Actual Outlet Name'] = ''
            else:
                output_row['Name Result'] = 'Warning'

            address_portal = str(portal_record.get('address', '')).strip()
            output_row['Actual Address'] = address_portal
            if not outlet_name_sheet:
                output_row['Address Result'] = 'False'
            elif outlet_name_sheet.lower() in address_portal.lower():
                output_row['Address Result'] = 'True'
                output_row['Actual Address'] = ''
            else:
                output_row['Address Result'] = 'Warning'

            if not output_row['Status']:
                output_row['Status'] = portal_record.get('status', 'Unknown')
            output_row['Integration Status'] = portal_record.get(
                'modelType', 'Unknown')

        else:
            output_row['Status'] = 'Not Found in Portal Scrape'
            output_row['Name Result'] = 'False'
            output_row['Address Result'] = 'False'

        results.append(output_row)

    log.success("Validation complete for this batch.")
    return pd.DataFrame(results)


# --- Main Execution ---
if __name__ == "__main__":
    print("=" * 70)
    print("=== Grab Merchant Validator (Batch Mode with Separate Sheets) ===")
    print("=" * 70)

    gsheet_client = ServiceFactory.get_sheets_client()
    grab_scraper = ServiceFactory.get_grab_scraper()

    input_df = gsheet_client.read_worksheet_as_dataframe(
        GOOGLE_SHEET_NAME, INPUT_WORKSHEET_NAME)
    if input_df is None:
        log.error("Could not read input data from Google Sheet. Exiting.")
        if grab_scraper:
            grab_scraper.quit()
        exit()

    all_tasks = restructure_data(input_df)
    if not all_tasks:
        log.error("No tasks were created from the input data. Exiting.")
        if grab_scraper:
            grab_scraper.quit()
        exit()

    if not grab_scraper or not grab_scraper.driver:
        log.fatal("Browser session failed to initialize. Exiting.")
        exit()

    try:
        while True:
            account_list = list(grab_scraper.credentials.keys())
            print("\n" + "=" * 70)
            log.info("Please select an option:")

            print("   1. Run All Accounts")
            for i, name in enumerate(account_list):
                print(f"   {i+2}. {name}")
            print(f"   {len(account_list) + 2}. Exit")
            print("=" * 70)

            choice_input = input(f"Enter number (1-{len(account_list) + 2}): ")
            try:
                choice = int(choice_input)
            except ValueError:
                log.error("Invalid input. Please enter a number.")
                continue

            accounts_to_process = []
            if choice == 1:
                log.info("Option selected: Run All Accounts.")
                accounts_to_process = account_list
            elif 2 <= choice <= len(account_list) + 1:
                selected_account = account_list[choice - 2]
                log.info(f"Option selected: Run account '{selected_account}'.")
                accounts_to_process.append(selected_account)
            elif choice == len(account_list) + 2:
                log.info("Exit choice selected.")
                break
            else:
                log.error(
                    f"Invalid choice '{choice_input}'. Please try again.")
                continue

            for account_name in accounts_to_process:
                print("-" * 70)
                log.info(
                    f"--- Starting processing for account: {account_name} ---")

                tasks_for_selected_account = [
                    task for task in all_tasks if task['source_portal'] == account_name
                ]
                if not tasks_for_selected_account:
                    log.warn(
                        f"No tasks found for account '{account_name}' in the input sheet. Skipping.")
                    continue

                log.info(
                    f"Found {len(tasks_for_selected_account)} tasks for this account.")

                try:
                    if grab_scraper.login(account_name):
                        merchants_data = grab_scraper.collect_data()

                        if merchants_data is None:
                            log.info(
                                f"'{account_name}' is a single-outlet account. Writing 'False' report.")
                            report_df = create_single_outlet_report(
                                tasks_for_selected_account)
                            gsheet_client.write_dataframe_to_worksheet(report_df,
                                                                       GOOGLE_SHEET_NAME, account_name)
                            log.info(
                                f"✅ Report for {account_name} saved successfully!")

                        elif merchants_data:
                            log.info(
                                f"Data collection complete! Found {len(merchants_data)} total merchants in portal.")
                            portal_df = pd.DataFrame(merchants_data).drop_duplicates(
                                subset=['merchantID'])
                            log.info(
                                f"-> {len(portal_df)} unique merchants to be used for validation.")

                            report_df = perform_validation(
                                portal_df, tasks_for_selected_account)

                            if not report_df.empty:
                                gsheet_client.write_dataframe_to_worksheet(report_df,
                                                                           GOOGLE_SHEET_NAME, account_name)
                                log.info(
                                    f"✅ Report for {account_name} saved successfully!")
                            else:
                                log.warning(
                                    "Validation produced no results. Nothing to write.")

                        else:
                            log.error(
                                f"No merchant data collected from portal for account '{account_name}'.")
                    else:
                        log.warn(
                            f"Login failed for account '{account_name}'. Skipping.")
                except Exception as e:
                    log.fatal(
                        f"An unexpected error occurred during processing for {account_name}: {e}")

            if accounts_to_process:
                log.info("Batch finished. Returning to main menu.")
    finally:
        if grab_scraper:
            grab_scraper.quit()
        log.info("Process finished.")
