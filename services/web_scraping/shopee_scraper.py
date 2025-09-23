import gzip
import json
import os
import random
import re
import time
from typing import Any, Dict, List, Optional

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from services.web_scraping.base_browser import BaseBrowserSession
from services.config import SHOPEE_PARTNER_CONFIG
from services.web_scraping.settings import SHOPEE_API_PATTERN


class ShopeeScraper(BaseBrowserSession):
    def __init__(self, credentials: Dict[str, Dict[str, str]], config: Optional[Dict[str, Any]] = None):
        super().__init__(config or SHOPEE_PARTNER_CONFIG)
        self.credentials = credentials

    def login(self, account_name: str) -> bool:
        account_creds = self.credentials.get(account_name)
        if not account_creds:
            self.logger.error(
                f"Credentials not found for account: {account_name}")
            return False

        if self.current_account == account_name:
            self.logger.info(
                f"✅ Already logged in with {account_name} account.")
            return True
        elif self.current_account is not None:
            self.logger.info(
                f"🔄 Switching accounts from {self.current_account} to {account_name}.")

        self.logger.info(
            f"🔑 Attempting to log in with {account_name} account...")
        self.safe_get(self.config['login_url'])

        try:
            time.sleep(random.uniform(2.0, 4.0))
            if "/select" not in self.driver.current_url and "/food/dashboard" not in self.driver.current_url:
                self.logger.info("  ➡️ Entering credentials...")
                username_field = self.wait.until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'input[placeholder="No. handphone / Username / Email"]')))
                username_field.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                username_field.send_keys(account_creds["username"])
                password_field = self.wait.until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'input[placeholder="Password"]')))
                password_field.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                password_field.send_keys(account_creds["password"])
                self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(., 'Masuk')]"))).click()
                try:
                    self.wait(5).until(EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(., 'Lanjutkan')]"))).click()
                    self.logger.info(
                        "  ➡️ Clicked optional 'Continue' button.")
                except TimeoutException:
                    pass

            time.sleep(random.uniform(2.0, 3.0))
            if "/food/dashboard" not in self.driver.current_url:
                self.logger.info("  ➡️ Selecting merchant profile...")
                profile_selector = (By.CSS_SELECTOR, 'div.listItem')
                merchant_profile = self.wait.until(
                    EC.visibility_of_element_located(profile_selector))
                ActionChains(self.driver).move_to_element(merchant_profile).pause(
                    random.uniform(0.5, 1.0)).click().perform()

            self.wait.until(EC.url_contains('/food/dashboard'))
            self.logger.info(f"✅ Login successful for {account_name}.")
            self.current_account = account_name
            return True
        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(
                f"❌ Error during login for {account_name}. Details: {e}")
            return False

    def collect_data(self) -> Optional[List[Dict[str, Any]]]:
        self.logger.info("  Navigating to Shopee POS page...")
        try:
            self.safe_get(self.config['pos_url'])
            try:
                self.wait(10).until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[span[text()='OK']]"))).click()
                time.sleep(random.uniform(1.5, 2.5))
            except TimeoutException:
                pass

            del self.driver.requests
            self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'div.shop-select-preview'))).click()
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class, 'select-dropdown-item')]"))).click()

            api_pattern = re.compile(SHOPEE_API_PATTERN)
            request = self.driver.wait_for_request(api_pattern, timeout=30)

            if not request.response:
                return None
            body = gzip.decompress(request.response.body).decode('utf-8') if request.response.headers.get(
                'Content-Encoding') == 'gzip' else request.response.body.decode('utf-8')
            data = json.loads(body).get('data', {})

            stores = data.get('stores') or (
                [data.get('store')] if data.get('store') else [])
            self.logger.info(
                f"  Successfully captured data for {len(stores)} stores.")
            return stores
        except Exception as e:
            self.logger.error(
                f"  An error occurred while collecting store data: {e}")
            return None

    def logout(self):
        # Shopee does not have a clean logout URL, relies on session clearing
        self.logger.info(f"Clearing session for {self.current_account}")
        self.current_account = None
        # The profile management will handle clearing the session data
        pass
