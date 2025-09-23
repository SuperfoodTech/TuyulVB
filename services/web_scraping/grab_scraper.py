import json
import time
from typing import Any, Dict, List, Optional

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from services.web_scraping.base_browser import BaseBrowserSession
from services.config import GRAB_MERCHANT_CONFIG, TARGET_API_URL, SINGLE_OUTLET_CHECK_URL


class GrabScraper(BaseBrowserSession):
    def __init__(self, credentials: Dict[str, Dict[str, str]], config: Optional[Dict[str, Any]] = None):
        super().__init__(config or GRAB_MERCHANT_CONFIG)
        self.credentials = credentials

    def handle_welcome_modal(self):
        """Looks for a specific 'Tutup' welcome modal and closes it."""
        try:
            short_wait = self.wait(10)
            close_button_xpath = "//button[span[text()='Tutup'] or contains(@class, 'btn-skip')]"

            self.logger.info("   Checking for the welcome modal...")
            welcome_modal_button = short_wait.until(
                EC.element_to_be_clickable((By.XPATH, close_button_xpath))
            )
            welcome_modal_button.click()
            self.logger.info("   Closed the welcome modal.")
            time.sleep(1)
        except TimeoutException:
            self.logger.info("   Welcome modal not found, proceeding.")
            pass

    def login(self, account_name: str) -> bool:
        """Handles the full login flow for a given account and navigates to the starting page."""
        account_creds = self.credentials.get(account_name)
        if not account_creds:
            self.logger.error(
                f"Credentials not found for account: {account_name}")
            return False

        if self.current_account == account_name:
            self.logger.info(
                f"✅ Already logged in with {account_name} account.")
            if not self.safe_get(self.config['merchant_list_url']):
                self.logger.error("Failed to re-navigate to the menu page.")
                return False
            return True

        if self.current_account is not None:
            self.logger.info(
                f"🔄 Switching accounts. Logging out from {self.current_account} first...")
            self.logout()

        self.logger.info(
            f"🔑 Attempting to log in with {account_name} account...")
        if not self.safe_get(self.config["login_url"]):
            return False

        try:
            self.handle_generic_popups()

            try:
                self.logger.info(
                    "   Checking for Login as another user button...")
                another_user_button_wait = self.wait(2)
                another_user_button = another_user_button_wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//p[text()='Login as another user'] | //div[text()='Login as another user']")))
                another_user_button.click()
                self.logger.info("   Clicked Login as another user.")
            except (TimeoutException, NoSuchElementException):
                self.logger.info(
                    "   No Login as another user button found, proceeding.")

            self.logger.info("   ➡️ Entering username...")
            username_field = self.wait.until(EC.visibility_of_element_located(
                (By.ID, self.config["username_field_id"])))
            username_field.clear()
            username_field.send_keys(account_creds["username"])
            self.logger.info("   ➡️ Clicking continue after username...")
            continue_user_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, self.config["continue_after_username_xpath"])))
            continue_user_button.click()

            self.logger.info("   ➡️ Entering password...")
            password_field = self.wait.until(EC.visibility_of_element_located(
                (By.ID, self.config["password_field_id"])))
            password_field.clear()
            password_field.send_keys(account_creds["password"])

            self.logger.info("   ➡️ Clicking continue after password...")
            final_login_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, self.config["continue_after_password_xpath"])))
            final_login_button.click()

            self.wait.until(EC.url_contains(
                "https://merchant.grab.com/dashboard"))
            if "login" in self.driver.current_url.lower():
                self.logger.error(
                    "Login failed. Check credentials or solve CAPTCHA.")
                return False

            self.logger.info(f"✅ Login successful for {account_name}.")
            self.current_account = account_name
            self.handle_welcome_modal()

            self.logger.info(
                f"Navigating to menu page: {self.config['merchant_list_url']}")
            if not self.safe_get(self.config['merchant_list_url']):
                self.logger.error(
                    "Failed to navigate to the menu page after login.")
                return False

            return True
        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(
                f"❌ Error during login for {account_name}: A step failed. Check selectors. Details: {e}")
            self.current_account = None
            return False

    def logout(self):
        """Handles the logout process by navigating to the logout URL."""
        if self.current_account is None:
            return

        self.logger.info(
            f"🔒 Logging out from {self.current_account} account...")
        try:
            if self.safe_get(self.config["logout_url"]):
                time.sleep(3)
            self.logger.info("✅ Logout successful.")
            self.current_account = None
        except Exception as e:
            self.logger.error(f"❌ Could not log out cleanly. Details: {e}")
            self.current_account = None

    def collect_data(self) -> Optional[List[Dict[str, Any]]]:
        self.logger.info(
            "Starting data collection with sequential API check...")
        del self.driver.requests

        try:
            self.logger.info(
                "Attempting to capture the main multi-outlet API (timeout: 10s)...")
            request = self.driver.wait_for_request(
                TARGET_API_URL, timeout=10)

            self.logger.info(
                "Main search API was called. Proceeding with full data collection.")
            data = json.loads(request.response.body.decode('utf-8'))
            merchants_batch = data.get("merchants", [])
            has_more_data = data.get("hasMore", False)

            if len(merchants_batch) == 1 and not has_more_data:
                self.logger.warning(
                    "Main API confirms only 1 outlet. Treating as single-outlet account.")
                return None

            all_merchants = merchants_batch
            if not has_more_data:
                self.logger.info(
                    "Main API indicates all data was collected in the first request.")
                return all_merchants

            try:
                scrollable_element = self.driver.find_element(
                    By.CSS_SELECTOR, "div.dui-table-body")
            except NoSuchElementException:
                self.logger.error(
                    "Could not find scrollable element even though API indicated more data.")
                return all_merchants

            page_scroll_attempts = 0
            while has_more_data:
                previous_merchant_count = len(all_merchants)
                del self.driver.requests
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_element)
                try:
                    scroll_request = self.driver.wait_for_request(
                        TARGET_API_URL, timeout=60)
                    if scroll_request and scroll_request.response:
                        data = json.loads(
                            scroll_request.response.body.decode('utf-8'))
                        merchants_batch = data.get("merchants", [])
                        if merchants_batch:
                            all_merchants.extend(merchants_batch)
                        if len(all_merchants) == previous_merchant_count:
                            page_scroll_attempts += 1
                            if page_scroll_attempts > 2:
                                self.logger.error(
                                    "No new merchants after multiple scroll attempts. Forcing stop.")
                                break
                        else:
                            page_scroll_attempts = 0
                        has_more_data = data.get("hasMore", False)
                except (json.JSONDecodeError, TimeoutException):
                    self.logger.warning(
                        "Timed out or failed to decode response while scrolling. Assuming no more data.")
                    break
            return all_merchants

        except TimeoutException:
            self.logger.info(
                "Main API not found. Checking for the single-outlet portal API (timeout: 20s)...")

            try:
                request = self.driver.wait_for_request(
                    SINGLE_OUTLET_CHECK_URL, timeout=20)
                self.logger.info(
                    "Portal API was called, indicating a single-outlet account.")
                return None
            except TimeoutException:
                self.logger.error(
                    "Did not capture any merchant data API call within the timeout period.")
                return []

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode API response. Error: {e}")
            return []

        return []
