import json
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config import settings
from utils.logging import log
from services.base.exceptions import AuthenticationError, DataCollectionError
from .base_browser import BaseBrowserSession


class GrabScraper(BaseBrowserSession):
    """Manages the browser lifecycle for the Grab Merchant Portal."""

    def _safe_get(self, url):
        try:
            self.driver.get(url)
            return True
        except TimeoutException:
            log("error", f"Page took too long to load: {url}")
            return False

    def _handle_welcome_modal(self):
        try:
            close_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(
                (By.XPATH, "//button[span[text()='Tutup'] or contains(@class, 'btn-skip')]")))
            close_button.click()
            log("info", "Closed the welcome modal.")
            time.sleep(1)
        except TimeoutException:
            log("info", "Welcome modal not found, proceeding.")

    def login(self, account_name, account_creds):
        portal_config = settings.GRAB_MERCHANT_CONFIG
        if self.current_account == account_name: return True
        if self.current_account is not None: self.logout()

        log("info", f"Attempting to log in with {account_name} account...")
        if not self._safe_get(portal_config["login_url"]):
            raise AuthenticationError("Failed to load login page.")

        try:
            try:
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(
                    (By.XPATH, "//p[text()='Login as another user'] | //div[text()='Login as another user']"))).click()
            except (TimeoutException, NoSuchElementException): pass
            self.wait.until(EC.visibility_of_element_located(
                (By.ID, portal_config["username_field_id"]))).send_keys(account_creds["username"])
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, portal_config["continue_after_username_xpath"]))).click()
            self.wait.until(EC.visibility_of_element_located(
                (By.ID, portal_config["password_field_id"]))).send_keys(account_creds["password"])
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, portal_config["continue_after_password_xpath"]))).click()
            self.wait.until(EC.url_contains(
                "https://merchant.grab.com/portal"))
            log("success", f"Login successful for {account_name}.")
            self.current_account = account_name
            self._handle_welcome_modal()
            if not self._safe_get(portal_config['merchant_list_url']):
                raise AuthenticationError(
                    "Failed to navigate to the menu page after login.")
            return True
        except (TimeoutException, NoSuchElementException) as e:
            raise AuthenticationError(
                f"Error during login for {account_name}: {e}") from e

    def logout(self):
        if self.current_account is None: return
        log("info", f"Logging out from {self.current_account} account...")
        self._safe_get(settings.GRAB_MERCHANT_CONFIG["logout_url"])
        time.sleep(3)
        self.current_account = None

    def collect_data(self):
        log("info", "Starting data collection, waiting for merchant API call...")
        del self.driver.requests
        try:
            request = self.driver.wait_for_request(
                settings.TARGET_API_URL, timeout=30)
            log("info", "Multi-outlet API found. Processing...")
            data = json.loads(request.response.body.decode('utf-8'))
            all_merchants = data.get("merchants", [])
            has_more = data.get("hasMore", False)
            if has_more:
                scrollable_element = self.driver.find_element(
                    By.CSS_SELECTOR, "div.dui-table-body")
                while has_more:
                    del self.driver.requests
                    self.driver.execute_script(
                        "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_element)
                    try:
                        scroll_request = self.driver.wait_for_request(
                            settings.TARGET_API_URL, timeout=60)
                        if scroll_request.response:
                            data = json.loads(
                                scroll_request.response.body.decode('utf-8'))
                            all_merchants.extend(data.get("merchants", []))
                            has_more = data.get("hasMore", False)
                    except TimeoutException: break
            return all_merchants, 'MULTI_OUTLET'
        except TimeoutException:
            log("info", "Multi-outlet API not found. Checking for single-outlet API...")
            try:
                request = self.driver.wait_for_request(
                    settings.SINGLE_OUTLET_CHECK_URL, timeout=20)
                if request.response:
                    merchants = json.loads(request.response.body.decode(
                        'utf-8')).get("merchants", [])
                    return merchants, 'SINGLE_OUTLET'
            except TimeoutException:
                raise DataCollectionError(
                    "Did not capture any merchant data API call.")
        except (json.JSONDecodeError, NoSuchElementException) as e:
            raise DataCollectionError(
                f"Failed to get merchant data. Error: {e}") from e
        return [], 'ERROR'
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
