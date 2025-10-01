import json
import time
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from utils import log
import settings


class BrowserSession:
    """Manages the browser lifecycle, including login, logout, and navigation."""

    def __init__(self):
        log("info", "🚀 Initializing browser...")
        try:
            service = Service(ChromeDriverManager().install())
            options = webdriver.ChromeOptions()
            options.add_argument('--log-level=3')
            options.add_experimental_option(
                'excludeSwitches', ['enable-logging'])
            options.add_argument(
                '--disable-blink-features=AutomationControlled')
            self.driver = webdriver.Chrome(
                service=service, options=options, seleniumwire_options={'disable_encoding': True})
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 20)
            self.current_account = None
        except Exception as e:
            log("fatal", f"Failed to initialize browser session: {e}")
            self.driver = None

    def safe_get(self, url):
        try:
            self.driver.get(url)
            return True
        except TimeoutException:
            log("error", f"Page took too long to load: {url}")
            return False

    def handle_welcome_modal(self):
        try:
            short_wait = WebDriverWait(self.driver, 10)
            close_button_xpath = "//button[span[text()='Tutup'] or contains(@class, 'btn-skip')]"
            welcome_modal_button = short_wait.until(
                EC.element_to_be_clickable((By.XPATH, close_button_xpath)))
            welcome_modal_button.click()
            log("info", "Closed the welcome modal.")
            time.sleep(1)
        except TimeoutException:
            log("info", "Welcome modal not found, proceeding.")

    def login(self, account_name, account_creds):
        portal_config = settings.GRAB_MERCHANT_CONFIG
        if self.current_account == account_name:
            return True
        if self.current_account is not None:
            self.logout()

        log("info", f"Attempting to log in with {account_name} account...")
        if not self.safe_get(portal_config["login_url"]):
            return False

        try:
            try:
                another_user_button_wait = WebDriverWait(self.driver, 5)
                another_user_button = another_user_button_wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//p[text()='Login as another user'] | //div[text()='Login as another user']")))
                another_user_button.click()
            except (TimeoutException, NoSuchElementException):
                pass

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
            self.handle_welcome_modal()

            if not self.safe_get(portal_config['merchant_list_url']):
                log("error", "Failed to navigate to the menu page after login.")
                return False
            return True
        except (TimeoutException, NoSuchElementException) as e:
            log("error", f"Error during login for {account_name}: {e}")
            self.current_account = None
            return False

    def logout(self):
        if self.current_account is None:
            return
        log("info", f"Logging out from {self.current_account} account...")
        self.safe_get(settings.GRAB_MERCHANT_CONFIG["logout_url"])
        time.sleep(3)
        self.current_account = None

    def quit(self):
        if self.driver:
            log("info", "Closing browser.")
            self.driver.quit()


def collect_all_merchants(driver):
    """Actively waits for and intercepts API calls to extract merchant data."""
    log("info", "Starting data collection, waiting for merchant API call...")
    del driver.requests
    try:
        request = driver.wait_for_request(settings.TARGET_API_URL, timeout=30)
        log("info", "Multi-outlet API found. Processing...")
        data = json.loads(request.response.body.decode('utf-8'))
        all_merchants = data.get("merchants", [])
        has_more = data.get("hasMore", False)

        if has_more:
            log("info", "More data available, scrolling to load all outlets...")
            scrollable_element = driver.find_element(
                By.CSS_SELECTOR, "div.dui-table-body")
            while has_more:
                del driver.requests
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_element)
                try:
                    scroll_request = driver.wait_for_request(
                        settings.TARGET_API_URL, timeout=60)
                    if scroll_request.response:
                        data = json.loads(
                            scroll_request.response.body.decode('utf-8'))
                        all_merchants.extend(data.get("merchants", []))
                        has_more = data.get("hasMore", False)
                except TimeoutException:
                    log("warn", "Timed out waiting for API response while scrolling. Assuming no more data.")
                    break
        return all_merchants, 'MULTI_OUTLET'
    except TimeoutException:
        log("info", "Multi-outlet API not found. Checking for single-outlet API...")
        try:
            request = driver.wait_for_request(
                settings.SINGLE_OUTLET_CHECK_URL, timeout=20)
            log("info", "Single-outlet API found. Processing...")
            if request.response:
                merchants = json.loads(request.response.body.decode(
                    'utf-8')).get("merchants", [])
                return merchants, 'SINGLE_OUTLET'
        except TimeoutException:
            log("error", "Did not capture any merchant data API call.")
    except (json.JSONDecodeError, NoSuchElementException) as e:
        log("error", f"Failed to get merchant data. Error: {e}")
    return [], 'ERROR'
