"""
Automated scheduler for force_open.py
Runs force_open for ALL merchants every 15 minutes continuously.
"""

import os
import sys
import time
import logging
from datetime import datetime
import schedule

# --- Setup Project Path ---
# Find project root by looking for common/ folder
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):  # Stop at drive root
    if os.path.isdir(os.path.join(PROJECT_ROOT, "common")):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.logger import get_logger
from modules.shopee.browser_session import BrowserSession
from config.settings_shopee import MERCHANT_PROCESSING_LIST
from modules.shopee.force_open.refactored import run_force_open
from modules.shopee.force_open.config_loader import load_config
from common.shopee_utils import switch_merchant

log = get_logger("force_open_scheduler")
log.propagate = False

# Load configuration from config.json
config = load_config()
INTERVAL_MINUTES = config.get("INTERVAL_MINUTES")
SCALE_LEVEL = config.get("SCALE_LEVEL")
DRY_RUN = config.get("DRY_RUN")
HEADLESS_MODE = config.get("HEADLESS_MODE")  # Set to False to see browser window


class ForceOpenScheduler:
    def __init__(self):
        self.session = None
        self.merchants = MERCHANT_PROCESSING_LIST
        self.run_count = 0
        log.info(
            f"Scheduler initialized with {len(self.merchants)} merchants. "
            f"Interval: {INTERVAL_MINUTES} minutes. DRY_RUN: {DRY_RUN}. HEADLESS: {HEADLESS_MODE}"
        )

    def initialize_session(self):
        """Initialize browser session once and reuse it."""
        if self.session is None or self.session.driver is None:
            log.info("Initializing browser session...")
            self.session = BrowserSession(headless=HEADLESS_MODE)

            if self.session.driver is None:
                log.error("Failed to initialize browser. Exiting.")
                return False

            # Login with master account
            if not self._login_master_account():
                log.error("Failed to login. Exiting.")
                self.close_session()
                return False

        return True

    def _login_master_account(self):
        """Login with the first (master) account."""
        if not self.merchants:
            log.error("No merchants configured.")
            return False

        try:
            # The system assumes the first merchant uses the master account
            log.info("Logging in with master account...")
            self.session.ensure_logged_in()
            return True
        except Exception as e:
            log.error(f"Login failed: {e}")
            return False

    def close_session(self):
        """Close the browser session."""
        if self.session and self.session.driver:
            try:
                log.info("Closing browser session...")
                self.session.quit()
            except Exception as e:
                log.warning(f"Error closing session: {e}")
            finally:
                self.session = None

    def run_all_merchants(self):
        """Run force_open for all merchants in sequence."""
        self.run_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log.info("=" * 80)
        log.info(f"RUN #{self.run_count} - {timestamp}")
        log.info("=" * 80)

        # Initialize session if not already done
        if not self.initialize_session():
            log.error(
                "Cannot proceed without valid session. Retrying on next interval."
            )
            return

        for i, merchant_task in enumerate(self.merchants, 1):
            merchant_name = merchant_task.get("output_name", "Unknown")
            validate_name = merchant_task.get("validate_name", merchant_name)
            log.info(f"\n[{i}/{len(self.merchants)}] Processing: {merchant_name}")

            try:
                # Check if still logged in before switching merchants
                if not self.session.ensure_logged_in():
                    log.error(
                        f"Failed to ensure login before switching to {merchant_name}. Skipping."
                    )
                    continue

                if not switch_merchant(
                    self.session.driver, self.session.wait, merchant_task
                ):
                    log.error(f"Failed to switch to {merchant_name}. Skipping.")
                    continue

                # Extract tokens and process stores
                run_force_open(
                    session=self.session,
                    merchant_task=merchant_task,
                    scale_level=SCALE_LEVEL,
                    dry_run=DRY_RUN,
                )

                log.info(f"✅ Completed: {merchant_name}")

            except Exception as e:
                log.error(f"❌ Error processing {merchant_name}: {e}")
                # Attempt to recover by reinitializing session on next iteration
                if self.session and self.session.driver:
                    try:
                        self.session.driver.get(
                            "https://partner.shopee.co.id/food/dashboard"
                        )
                    except Exception as recovery_error:
                        log.warning(f"Failed to recover session: {recovery_error}")
                        self.close_session()
                continue

            # Small delay between merchants to avoid rate limiting
            time.sleep(2)

        log.info("=" * 80)
        log.info(
            f"Run #{self.run_count} completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        log.info("=" * 80)

    def start(self):
        """Start the scheduler."""
        log.info(f"Starting scheduler. Will run every {INTERVAL_MINUTES} minutes.")
        log.info("Press Ctrl+C to stop.")

        # Schedule the job
        schedule.every(INTERVAL_MINUTES).minutes.do(self.run_all_merchants)

        # Run immediately on startup
        self.run_all_merchants()

        # Keep the scheduler running
        try:
            while True:
                schedule.run_pending()
                time.sleep(10)  # Check every 10 seconds if a job is due
        except KeyboardInterrupt:
            log.info("\n⏹️  Scheduler stopped by user.")
            self.close_session()
            log.info("Browser session closed. Exiting.")
        except Exception as e:
            log.error(f"Scheduler error: {e}")
            self.close_session()
            raise


def main():
    """Entry point for the scheduler."""
    # Remove default root logger handlers
    logging.getLogger().handlers = []

    try:
        scheduler = ForceOpenScheduler()
        scheduler.start()
    except Exception as e:
        log.critical(f"Fatal error in scheduler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
