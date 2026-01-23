"""
Automated scheduler for force_open.py
Runs force_open for ALL merchants:
1. On a fixed interval (e.g., every 15 minutes).
2. IMMEDIATELY if changes are detected in Monday.com status columns.
"""

import os
import sys
import time
import logging
import json
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
from common.monday_utils import fetch_board_items
from modules.shopee.browser_session import BrowserSession
from config.settings_shopee import MERCHANT_PROCESSING_LIST
from modules.shopee.force_open.refactored import run_force_open
from modules.shopee.force_open.config_loader import load_config
from common.shopee_utils import switch_merchant
from common.monday_utils import filter_items_by_check_level

log = get_logger("force_open_scheduler")
log.propagate = False

# Load configuration from config.json
config = load_config()
INTERVAL_MINUTES = config.get("INTERVAL_MINUTES")
SCALE_LEVEL = config.get("SCALE_LEVEL")
DRY_RUN = config.get("DRY_RUN")
HEADLESS_MODE = config.get("HEADLESS_MODE")

STATE_FILE_PATH = os.path.join(PROJECT_ROOT, "data", "cache", "force_open_state.json")


class ForceOpenScheduler:
    def __init__(self):
        self.session = None
        self.merchants = MERCHANT_PROCESSING_LIST
        self.run_count = 0
        self.is_running = False

        # Monday.com Config for Monitoring
        self.monday_board_id = config.get("MONDAY_BOARD_ID")
        self.group_id = config.get("GROUP_ID")
        self.check_col_id = config.get("CHECK_COL_ID")
        self.closed_req_col_id = config.get("CLOSED_REQ_COL_ID")

        # State Cache: {item_id: closed_req_value}
        self.state_cache = self._load_state()

        log.info(
            f"Scheduler initialized. "
            f"Interval: {INTERVAL_MINUTES}m. Monitor: Active (1m poll). "
            f"DRY_RUN: {DRY_RUN}. HEADLESS: {HEADLESS_MODE}"
        )

    def _load_state(self):
        """Load state from JSON file."""
        if os.path.exists(STATE_FILE_PATH):
            try:
                with open(STATE_FILE_PATH, "r") as f:
                    state = json.load(f)
                log.info(f"Loaded previous state from {STATE_FILE_PATH}")
                return state
            except Exception as e:
                log.error(f"Failed to load state file: {e}")
        return {}

    def _save_state(self):
        """Save current state to JSON file."""
        try:
            with open(STATE_FILE_PATH, "w") as f:
                json.dump(self.state_cache, f, indent=4)
            log.debug(f"State saved to {STATE_FILE_PATH}")
        except Exception as e:
            log.error(f"Failed to save state file: {e}")

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

    def _driver_creator(self):
        """Factory that returns a logged-in BrowserSession object for token extraction.

        Returns a BrowserSession instance (not the raw webdriver). `get_or_create_auth_tokens`
        understands this and will extract `driver` from it and call `quit()` on the session.
        """
        sess = BrowserSession(headless=HEADLESS_MODE)
        try:
            if sess.driver and sess.ensure_logged_in():
                return sess
        except Exception:
            pass
        return sess

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

    def get_monitoring_state(self):
        """
        Fetch current state of relevant items from Monday.com.
        Returns: dict {item_id: status_value}
        """
        try:
            items = fetch_board_items(self.monday_board_id, self.group_id)
            if not items:
                return None  # Distinguish empty from error if possible, but fetch_board_items returns [] on error too.

            # Use shared filter helper to apply the "Yes <level>" criteria
            current_state = {}
            filtered = filter_items_by_check_level(
                items, self.check_col_id, SCALE_LEVEL
            )
            for item, col_vals in filtered:
                try:
                    if col_vals and isinstance(col_vals, dict):
                        raw_val = col_vals.get(self.closed_req_col_id)
                    else:
                        raw_val = None

                    if raw_val is None:
                        req_val = ""
                    elif isinstance(raw_val, str):
                        req_val = raw_val.strip()
                    else:
                        # Convert other types to string and trim
                        req_val = str(raw_val).strip()

                except Exception as e:
                    log.debug(f"Unexpected column value for item {item.get('id')}: {e}")
                    req_val = ""

                current_state[item["id"]] = req_val

            return current_state
        except Exception as e:
            log.error(f"Error fetching Monday state: {e}")
            return None

    def check_for_changes(self):
        """
        Poll Monday.com for changes. If changes detected, trigger run.
        Runs frequently (e.g., every 1 minute).
        """
        if self.is_running:
            # Avoid stacking checks if a run is in progress
            return

        log.debug("Polling Monday.com for status changes...")
        current_state = self.get_monitoring_state()

        if current_state is None:
            log.warning("Failed to fetch Monday state during poll. Skipping.")
            return

        # If this is the first successful fetch, just populate cache and wait
        if not self.state_cache:
            self.state_cache = current_state
            self._save_state()
            return

        changes_detected = False

        # Check for modified or new items
        for item_id, new_val in current_state.items():
            old_val = self.state_cache.get(item_id)

            if item_id not in self.state_cache:
                log.info(f"🆕 New item detected (ID: {item_id}). Triggering run.")
                changes_detected = True
                break
            elif old_val != new_val:
                log.info(
                    f"🔄 Status change detected for Item {item_id}: '{old_val}' -> '{new_val}'. Triggering run."
                )
                changes_detected = True
                break

        # Check for removed items (optional: might not need immediate run, but we must update cache)
        if not changes_detected:
            if len(current_state) != len(self.state_cache):
                # An item was disabled or deleted. Just update cache, no need to trigger run (nothing to update on Shopee)
                log.info(
                    f"Item count changed ({len(self.state_cache)} -> {len(current_state)}). Updating cache."
                )
                self.state_cache = current_state
                self._save_state()
                return

        if changes_detected:
            log.info("⚡ Immediate execution triggered by Monday.com changes!")
            self.run_all_merchants()

        # Update cache is handled inside run_all_merchants, but if we didn't run, we should update here?
        # Actually, if we trigger run_all_merchants, it updates the cache at the end.
        # If we DON'T trigger, we should update cache here to reflect silent drops (disabled items).
        if not changes_detected:
            self.state_cache = current_state
            self._save_state()

    def run_all_merchants(self):
        """Run force_open for all merchants in sequence."""
        if self.is_running:
            log.warning("Run requested but is already in progress.")
            return

        self.is_running = True
        try:
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
                log.info(f"\n[{i}/{len(self.merchants)}] Processing: {merchant_name}")

                try:
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

                    run_force_open(
                        session=self.session,
                        merchant_task=merchant_task,
                        scale_level=SCALE_LEVEL,
                        dry_run=DRY_RUN,
                        driver_creator=self._driver_creator,
                    )
                    log.info(f"✅ Completed: {merchant_name}")

                except Exception as e:
                    log.error(f"❌ Error processing {merchant_name}: {e}")
                    # Attempt session recovery
                    if self.session and self.session.driver:
                        try:
                            self.session.driver.get(
                                "https://partner.shopee.co.id/food/dashboard"
                            )
                        except:
                            self.close_session()
                    continue

                time.sleep(2)

            log.info("=" * 80)
            log.info(
                f"Run #{self.run_count} completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            log.info("=" * 80)

            # Update state cache immediately after run to prevent re-triggering
            # if the poll happens right after. We want the "post-run" state.
            updated_state = self.get_monitoring_state()
            if updated_state:
                self.state_cache = updated_state
                self._save_state()
                log.debug("State cache updated after run.")

        finally:
            self.is_running = False

    def start(self):
        """Start the scheduler."""
        log.info(f"Starting scheduler.")
        log.info(f"1. Regular Interval: Every {INTERVAL_MINUTES} minutes")
        log.info(f"2. Change Monitor: Every 1 minute (Immediate Trigger)")
        log.info("Press Ctrl+C to stop.")

        # Populate initial cache
        log.info("Populating initial state cache...")
        initial_state = self.get_monitoring_state()
        if initial_state:
            self.state_cache = initial_state
            self._save_state()
            log.info(f"Initial state cached ({len(self.state_cache)} items monitored).")

        # Schedule jobs
        schedule.every(INTERVAL_MINUTES).minutes.do(self.run_all_merchants)
        schedule.every(1).minutes.do(self.check_for_changes)

        # Run immediately on startup
        self.run_all_merchants()

        try:
            while True:
                schedule.run_pending()
                time.sleep(5)
        except KeyboardInterrupt:
            log.info("\n⏹️  Scheduler stopped by user.")
            self.close_session()
        except Exception as e:
            log.error(f"Scheduler error: {e}")
            self.close_session()
            raise


def main():
    """Entry point for the scheduler."""
    logging.getLogger().handlers = []
    try:
        scheduler = ForceOpenScheduler()
        scheduler.start()
    except Exception as e:
        log.critical(f"Fatal error in scheduler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
