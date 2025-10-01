import os
from dotenv import load_dotenv
from config import credentials, settings
from utils import log
from grab_scraper import BrowserSession, collect_all_merchants
from monday_handler import write_to_monday_one_by_one


def main():
    """Main function to run the data extraction and upload process."""
    print("=" * 50)
    print("=== Grab Merchant Data Extractor & Monday.com Uploader ===")
    print("=" * 50)

    browser = BrowserSession()
    if not browser.driver:
        return

    while True:
        account_list = list(credentials.ACCOUNT_CREDS.keys())
        print("\n" + "=" * 70)
        log("info", "Please select an option:")
        print("     1. Run All Accounts")
        for i, name in enumerate(account_list):
            print(f"     {i+2}. {name}")
        print(f"     {len(account_list) + 2}. Exit")
        print("=" * 70)
        try:
            choice = int(input(f"Enter number (1-{len(account_list) + 2}): "))
        except ValueError:
            log("error", "Invalid input.")
            continue
        if choice == len(account_list) + 2:
            break
        accounts_to_process = account_list if choice == 1 else [
            account_list[choice - 2]] if 2 <= choice <= len(account_list) + 1 else []
        if not accounts_to_process:
            log("error", f"Invalid choice '{choice}'.")
            continue

        for account_name in accounts_to_process:
            print("-" * 70)
            log("info",
                f"--- Starting extraction for account: {account_name} ---")
            target_group_info = next(
                (g for g in settings.MONDAY_TARGET_GROUP if g['source_portal'] == account_name), None)
            if not target_group_info:
                log("error",
                    f"Monday.com group config not found for '{account_name}'. Skipping.")
                continue

            try:
                if browser.login(account_name, credentials.ACCOUNT_CREDS[account_name]):
                    merchants, api_type = collect_all_merchants(browser.driver)
                    if merchants:
                        log("success",
                            f"Data collection complete! Found {len(merchants)} merchants (Type: {api_type}).")
                        write_to_monday_one_by_one(
                            merchants, settings.MONDAY_BOARD_ID, target_group_info['group_id'], api_type)
                    else:
                        log("error",
                            f"No merchant data was collected for '{account_name}'.")
            except Exception as e:
                log("fatal",
                    f"A critical error occurred for '{account_name}': {e}")

        log("info", "Batch finished. Returning to main menu.")

    browser.quit()
    log("info", "Process finished.")


if __name__ == "__main__":
    load_dotenv(os.path.join(os.path.dirname(__file__), 'config', '.env'))
    main()
