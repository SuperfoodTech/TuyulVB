import os
import sys
import logging
import time
import argparse
import shutil

# --- Setup Project Path ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.logger import get_logger

try:
    from modules.shopee.browser_session import BrowserSession
    try:
        from config.credentials_shopee import ACCOUNT_CREDS
    except ImportError:
        ACCOUNT_CREDS = {}
    from config.settings_shopee import (
        MERCHANT_PROCESSING_LIST,
        MONDAY_BOARD_ID,
        GROUP_MAPPING,
    )
    from common.shopee_utils import get_current_merchant_name, switch_merchant
    from modules.shopee.extract_raw import run_raw_extraction
    from modules.shopee.force_open.refactored import run_force_open
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
    """Handles the logic for deleting the isolated Chromium profile."""
    profile_path = os.environ.get(
        "SHOPEE_SELENIUM_PROFILE_PATH",
        os.path.join(PROJECT_ROOT, "chromeprofile")
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
                return None, False
            except Exception as e:
                log.error(f"Could not delete profile folder: {e}")
    else:
        log.info("Profile folder does not exist.")
    return session, session is not None and session.driver is not None


def main(task_name, dry_run=False, scale_level=1):
    """Main execution block for Shopee tasks."""
    logging.getLogger().handlers = []

    task_map = {
        "extract_raw": run_raw_extraction,
        "force_open": run_force_open,
    }

    task_function = task_map.get(task_name)
    if not task_function:
        log.critical(f"Unknown Shopee task: '{task_name}'. Exiting.")
        return

    browser_session = None
    is_logged_in = False

    while True:
        merchants_to_process = []
        base_index = display_merchant_menu()
        log.setLevel(logging.CRITICAL)
        try:
            choice = int(input(f"Enter number (1-{base_index + 2}): "))
            log.setLevel(logging.INFO)
        except ValueError:
            log.setLevel(logging.INFO)
            log.error("Invalid input.")
            continue

        if choice == base_index + 2:
            log.info("Returning to main menu.")
            break
        elif choice == base_index + 1:
            browser_session, is_logged_in = handle_profile_reset(browser_session)
            continue
        elif choice == base_index:
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
            input()
            is_logged_in = True
            log.info("Manual login complete. You can now select a task to run.")
            continue

        if choice == 1:
            merchants_to_process = MERCHANT_PROCESSING_LIST
        elif 2 <= choice < base_index:
            merchants_to_process.append(MERCHANT_PROCESSING_LIST[choice - 2])
        else:
            log.error(f"Invalid choice '{choice}'. Please try again.")
            continue

        if browser_session is None:
            browser_session = BrowserSession()
        if not browser_session.driver:
            log.critical("Browser session failed to initialize.")
            break

        if not is_logged_in and ACCOUNT_CREDS:
            master_account_name = list(ACCOUNT_CREDS.keys())[0]
            if not browser_session.login(
                master_account_name, ACCOUNT_CREDS[master_account_name]
            ):
                log.critical("Master account login failed. Cannot proceed.")
                break
            is_logged_in = True

        for merchant_task in merchants_to_process:
            print("-" * 70)
            log.info(
                f"Starting task '{task_name}' for merchant: {merchant_task['validate_name']}",
            )

            current_merchant = get_current_merchant_name(
                browser_session.driver, browser_session.wait
            )
            switch_successful = False
            if current_merchant == merchant_task["validate_name"]:
                log.info("Already on the correct merchant dashboard. Skipping switch.")
                switch_successful = True
            else:
                switch_successful = switch_merchant(
                    browser_session.driver,
                    browser_session.wait,
                    merchant_task,
                )

            if switch_successful:
                if task_name == "force_open":
                    from common.data_provider import DataProviderFactory
                    provider = DataProviderFactory.create_provider()
                    task_function(
                        session=browser_session,
                        data_provider=provider,
                        scale_level=scale_level,
                        dry_run=dry_run,
                    )
                else:
                    task_function(browser_session, merchant_task)
            else:
                log.warning(
                    f"Could not switch to merchant {merchant_task['validate_name']}. Skipping.",
                )

    if browser_session:
        browser_session.quit()
    log.info("Shopee runner finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shopee Runner")
    parser.add_argument(
        "--task",
        default="extract_raw",
        choices=["extract_raw", "force_open"],
        help="The specific task to perform.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the task in dry-run mode.",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=1,
        help="Scale Level (1-5) for force_open task.",
    )
    args = parser.parse_args()
    main(args.task, args.dry_run, args.scale)