import os
import sys
import logging
import time
import argparse

# --- Setup Project Path ---
# This allows the script to be run directly and still find common modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import shutil
from common.logger import get_logger

try:
    # Shopee-specific modules
    from modules.shopee.browser_session import BrowserSession
    from config.credentials_shopee import ACCOUNT_CREDS
    from config.settings_shopee import (
        MERCHANT_PROCESSING_LIST,
        MONDAY_BOARD_ID,
        GROUP_MAPPING,
    )
    from common.shopee_utils import get_current_merchant_name, switch_merchant

    # Import the core logic functions from the refactored scripts
    from modules.shopee.sync_store_details import run_store_details_sync
    from modules.shopee.sync_short_names import run_short_names_sync
    from modules.shopee.shopee_customer import run_customer_details_sync
    from modules.shopee.address_validation import run_address_validation
    from modules.shopee.extract_raw import run_raw_extraction
    from modules.shopee.sync_address_klikit import (
        run_address_validation as run_klikit_validation,
    )
    from modules.shopee.sync_oph_klikit import run_oph_sync as run_klikit_oph
    from modules.shopee.sync_klikit_unified import (
        run_unified_sync as run_klikit_unified,
    )
    from modules.shopee.force_open.refactored import run_force_open
    from modules.shopee.shopee_menu_extract import run_menu_extraction, save_menu_data

except ImportError as e:
    print(f"[FATAL] An import failed: {e}. Ensure all config files are correct.")
    sys.exit(1)

# Use the centralized logger
log = get_logger("shopee_runner")
log.propagate = False


def display_merchant_menu():
    """Displays the menu for selecting which merchant(s) to process."""
    print("\n" + "=" * 70)
    log.info("Please select a merchant to process:")
    print("  1. Run All Merchants")
    for i, merchant in enumerate(MERCHANT_PROCESSING_LIST):
        print(f"  {i+2}. {merchant['output_name']}")
    base_index = len(MERCHANT_PROCESSING_LIST) + 2
    print("-" * 20)
    print(f"  {base_index}. Manual Login Setup")
    print(f"  {base_index + 1}. Reset Profile (Clear Session)")
    print(f"  {base_index + 2}. Exit to Main Menu")
    print("=" * 70)
    return base_index


def handle_profile_reset(session):
    """Handles the logic for deleting the Selenium profile."""
    profile_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "selenium_profiles",
        "shopee_profile",
    )
    if os.path.exists(profile_path):
        if input("  [WARNING] Delete profile folder? [y/N]: ").lower() == "y":
            try:
                if session and session.driver:
                    log.warning("Quitting active browser before deleting profile...")
                    session.quit()
                    time.sleep(1)
                shutil.rmtree(profile_path)
                log.info("✅ Profile folder deleted.")
                return None, False  # Return a cleared session and login status
            except Exception as e:
                log.error(f"Could not delete profile folder: {e}")
    else:
        log.info("Profile folder does not exist.")
    return session, session is not None and session.driver is not None


def main(task_name, dry_run=False, scale_level=1):
    """Main execution block for all Shopee-related tasks."""
    # Remove default root logger handlers to prevent double logging from imported libraries
    logging.getLogger().handlers = []

    task_map = {
        "sync_details": run_store_details_sync,
        "sync_short_names": run_short_names_sync,
        "sync_customers": run_customer_details_sync,
        "address_validation": run_address_validation,
        "klikit_validation": run_klikit_validation,
        "klikit_oph": run_klikit_oph,
        "klikit_unified": run_klikit_unified,
        "extract_raw": run_raw_extraction,
        "force_open": run_force_open,
        "shopee_menu_extract": run_menu_extraction,
    }

    task_function = task_map.get(task_name)
    if not task_function:
        log.critical(f"Unknown Shopee task: '{task_name}'. Exiting.")
        return

    # Tasks that do not require a browser session
    offline_tasks = [
        "sync_details",
        "klikit_validation",
        "klikit_oph",
        "klikit_grab_validation",
        "klikit_unified",
    ]

    browser_session = None
    is_logged_in = False

    while True:
        merchants_to_process = []
        # AUTO-RUN LOGIC: If task is menu extraction, default to all merchants and skip menu
        if task_name == "shopee_menu_extract":
             log.info("Task 'shopee_menu_extract' selected. Defaulting to 'Run All Merchants' per configuration.")
             merchants_to_process = MERCHANT_PROCESSING_LIST
             auto_run = True
        else:
             auto_run = False
             base_index = display_merchant_menu()
             # Temporarily disable logging while waiting for user input
             log.setLevel(logging.CRITICAL)
             try:
                 choice = int(input(f"Enter number (1-{base_index + 1}): "))
                 # Re-enable logging after input is received
                 log.setLevel(logging.INFO)
             except ValueError:
                 log.setLevel(logging.INFO)  # Re-enable logging on error
                 log.error("Invalid input.")
                 continue

             if choice == base_index + 2:
                 log.info("Returning to main menu.")
                 break
             elif choice == base_index + 1:
                 browser_session, is_logged_in = handle_profile_reset(browser_session)
                 continue
             elif choice == base_index:
                 if task_name not in offline_tasks:
                    log.info("Starting manual login setup...")
                    if browser_session and getattr(browser_session, "headless", True):
                        log.info("Switching to visible browser for manual login...")
                        browser_session.quit()
                        browser_session = None

                    if browser_session is None:
                        browser_session = BrowserSession(headless=False)

                    if not browser_session.driver:
                        log.critical("Browser session failed to initialize.")
                        break

                 browser_session.driver.get(
                    "https://partner.business.accounts.shopee.co.id/authenticate/login/"
                 )
                 log.warning(
                    "Please log in manually in the browser window. Press Enter here when you are done..."
                 )
                 input()  # Wait for user to press Enter
                 is_logged_in = True
                 log.info("Manual login complete. You can now select a task to run.")
                 continue

             if choice == 1:
                 merchants_to_process = MERCHANT_PROCESSING_LIST
             # Adjust the upper bound for merchant selection
             elif 2 <= choice < base_index:
                 merchants_to_process.append(MERCHANT_PROCESSING_LIST[choice - 2])
             else:
                 log.error(f"Invalid choice '{choice}'. Please try again.")
                 continue

        if task_name not in offline_tasks:
            if browser_session is None:
                browser_session = BrowserSession()
            if not browser_session.driver:
                log.critical("Browser session failed to initialize.")
                break

            if not is_logged_in:
                master_account_name = list(ACCOUNT_CREDS.keys())[0]
                if not browser_session.login(
                    master_account_name, ACCOUNT_CREDS[master_account_name]
                ):
                    log.critical("Master account login failed. Cannot proceed.")
                    break
                is_logged_in = True

        collected_results = []
        for merchant_task in merchants_to_process:
            print("-" * 70)
            log.info(
                f"Starting task '{task_name}' for merchant: {merchant_task['validate_name']}",
            )

            if task_name in offline_tasks:
                # Offline execution: No browser, no switching
                if task_name in [
                    "klikit_validation",
                    "klikit_oph",
                    "klikit_grab_validation",
                    "klikit_unified",
                ]:
                    task_function(None, merchant_task, dry_run=dry_run)
                else:
                    task_function(None, merchant_task)
                continue

            current_merchant = get_current_merchant_name(
                browser_session.driver, browser_session.wait
            )
            switch_successful = False
            if current_merchant == merchant_task["validate_name"]:
                log.info(
                    "  Already on the correct merchant dashboard. Skipping switch.",
                )
                switch_successful = True
            else:
                switch_successful = switch_merchant(
                    browser_session.driver,
                    browser_session.wait,
                    merchant_task,
                )

            if switch_successful:
                # Call the specific task function with the browser session and merchant info
                res = None
                if task_name == "force_open":
                    task_function(
                        browser_session,
                        merchant_task,
                        scale_level=scale_level,
                        dry_run=dry_run,
                    )
                else:
                    res = task_function(browser_session, merchant_task)
                
                # Collect results
                if res:
                    collected_results.append(res)
            else:
                log.warning(
                    f"Could not switch to merchant {merchant_task['validate_name']}. Skipping.",
                )
        
        # Post-processing: Aggregate results for Menu Extraction
        if task_name == "shopee_menu_extract" and collected_results:
             log.info("Aggregating results for Menu Extraction...")
             # collected_results is a list of lists (stores per portal)
             flattened_data = []
             for batch in collected_results:
                 if isinstance(batch, list):
                     flattened_data.extend(batch)
                 else:
                     log.warning(f"Unexpected result format from task: {type(batch)}")
             
             if flattened_data:
                 save_menu_data(flattened_data)
        
        if auto_run:
            break

    if browser_session:
        browser_session.quit()
    log.info("Shopee runner finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Centralized Shopee Scraper Runner")
    parser.add_argument(
        "--task",
        required=True,
        choices=[
            "sync_details",
            "sync_short_names",
            "sync_customers",
            "address_validation",
            "klikit_validation",
            "klikit_oph",
            "klikit_grab_validation",
            "klikit_unified",
            "extract_raw",
            "force_open",
            "shopee_menu_extract",
        ],
        help="The specific scraping task to perform.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the task in dry-run mode (no changes to Monday.com). Currently supported by: klikit_validation, klikit_oph, klikit_grab_validation, klikit_unified.",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=1,
        help="Scale Level (1-5) for force_open task. Defaults to 1.",
    )
    args = parser.parse_args()
    main(args.task, args.dry_run, args.scale)