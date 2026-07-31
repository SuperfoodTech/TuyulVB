"""
Automated Scheduler for ShopeeFood Auto Open & Auto Close Bot.
Runs periodic evaluation of all outlets based on Vercel Toggle & 5-Level Priority Engine.
"""

import os
import sys
import time
import logging
import schedule
from datetime import datetime

# Setup project path
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.isdir(os.path.join(PROJECT_ROOT, "common")):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.logger import get_logger
from common.data_provider import DataProviderFactory
from common.db_manager import DatabaseManager
from modules.shopee.browser_session import BrowserSession
from modules.shopee.force_open.refactored import run_force_open
from modules.shopee.force_open.config_loader import load_config

log = get_logger("force_open_scheduler")
log.propagate = False

config = load_config()
INTERVAL_SECONDS = int(os.environ.get("BOT_INTERVAL_SECONDS", os.environ.get("INTERVAL_SECONDS", config.get("INTERVAL_SECONDS", 60))))
DRY_RUN = config.get("DRY_RUN", False)
HEADLESS_MODE = config.get("HEADLESS_MODE", True)


class ForceOpenScheduler:
    """Manages scheduled execution of Auto Open & Auto Close cycles."""

    def __init__(self):
        self.session = None
        self.data_provider = DataProviderFactory.create_provider()
        self.db_manager = DatabaseManager()
        self.run_count = 0
        self.is_running = False
        self._token_refresh_fail_count = 0

        log.info(
            f"Scheduler initialized with Data Provider. "
            f"Interval: {INTERVAL_SECONDS}s. "
            f"DRY_RUN: {DRY_RUN}. HEADLESS: {HEADLESS_MODE}"
        )

    def initialize_session(self) -> bool:
        """Initializes browser session once, reuses it, and ensures Shopee login.
        Uses saved chromeprofile cookies — no OTP triggered for restored sessions.
        If session expires, auto-reconnects and re-validates via chromeprofile.
        """
        if self.session is None or self.session.driver is None:
            log.info("Initializing browser session...")
            try:
                self.session = BrowserSession(headless=HEADLESS_MODE)
                if self.session.driver is None:
                    log.error("Failed to initialize browser session.")
                    return False
                log.info("Browser session initialized successfully.")
            except Exception as e:
                log.error(f"Error initializing browser session: {e}")
                return False

        # Validate / restore Shopee login using saved chromeprofile (no OTP triggered)
        try:
            logged_in = self.session.ensure_logged_in(max_retries=2)
            if logged_in:
                log.info("✅ Shopee Partner session validated (chromeprofile auto-login).")
                self._token_refresh_fail_count = 0
                # Eagerly cache the fresh token for API calls
                from modules.shopee.api_utils import get_auth_tokens
                import json, os
                tob_token, entity_id = get_auth_tokens(driver=self.session.driver)
                if tob_token:
                    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "cache")
                    os.makedirs(cache_dir, exist_ok=True)
                    cache_path = os.path.join(cache_dir, "shopee_auth_tokens.json")
                    with open(cache_path, "w") as f:
                        json.dump({"shopee_tob_token": tob_token, "shopee_tob_entity_id": entity_id, "updated_at": datetime.now().isoformat()}, f)
                    log.info(f"✅ Shopee API token refreshed and cached (entity: {entity_id or 'n/a'}).")
                else:
                    log.warning("Session valid but tob_token not extracted — bot will use last cached token.")
            else:
                self._token_refresh_fail_count += 1
                log.warning(f"⚠️ Shopee login validation failed (attempt #{self._token_refresh_fail_count}). "
                            f"Bot will operate in data-only mode until session is restored.")
        except Exception as e:
            log.warning(f"Session health check skipped: {e}")

        return True

    def run_scheduled_job(self):
        """Executes a single cycle of store evaluations."""
        if self.is_running:
            log.warning("Job is already running. Skipping this execution cycle.")
            return

        self.is_running = True
        self.run_count += 1
        log.info(f"\n{'='*80}\nStarting Scheduled Job Execution #{self.run_count} [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n{'='*80}")

        try:
            # Ensure browser session is active and Shopee login is valid
            if not self.initialize_session():
                log.warning("Running job without active browser session (API mode / status check only).")

            # Run force open cycle with Data Provider & Priority Engine
            stats = run_force_open(
                session=self.session,
                data_provider=self.data_provider,
                dry_run=DRY_RUN,
                db_manager=self.db_manager
            )

            log.info(f"Scheduled Job Execution #{self.run_count} Completed.")
        except Exception as e:
            log.error(f"Error during scheduled job execution: {e}")
        finally:
            self.is_running = False


    def start(self):
        """Starts the scheduler loop."""
        log.info("Starting real-time scheduler loop...")
        self.run_scheduled_job()  # Run immediately once on start

        schedule.every(INTERVAL_SECONDS).seconds.do(self.run_scheduled_job)
        log.info(f"Job scheduled to run every {INTERVAL_SECONDS} seconds (Real-Time Mode). Press Ctrl+C to exit.")

        while True:
            try:
                schedule.run_pending()
                time.sleep(5)
            except KeyboardInterrupt:
                log.info("Scheduler stopped by user.")
                break
            except Exception as e:
                log.error(f"Unexpected error in scheduler loop: {e}")
                time.sleep(30)

        self.cleanup()

    def cleanup(self):
        """Cleans up resources."""
        log.info("Cleaning up scheduler resources...")
        if self.session:
            try:
                self.session.quit()
                log.info("Browser session closed.")
            except Exception as e:
                log.error(f"Error closing browser session: {e}")


def main():
    scheduler = ForceOpenScheduler()
    scheduler.start()


if __name__ == "__main__":
    main()
