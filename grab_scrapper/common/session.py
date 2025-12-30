import time
from datetime import datetime
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def log(level, message):
    """Prints a formatted message to the console."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level.upper()}] {message}")


class BrowserSession:
    """Manages the browser lifecycle for Grab portal, including login and logout."""

    def __init__(self, portal_config):
        log("info", "🚀 Initializing browser...")
        self.portal_config = portal_config
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--log-level=3")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])
            options.add_argument("--disable-blink-features=AutomationControlled")
            selenium_wire_options = {"disable_encoding": True}
            options.add_argument("--start-maximized")
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options,
                seleniumwire_options=selenium_wire_options,
            )
            self.driver.set_page_load_timeout(60)
            self.wait = WebDriverWait(self.driver, 30)
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
            close_button_xpath = (
                "//button[span[text()='Tutup'] or contains(@class, 'btn-skip')]"
            )
            welcome_modal_button = short_wait.until(
                EC.element_to_be_clickable((By.XPATH, close_button_xpath))
            )
            welcome_modal_button.click()
            log("info", "Closed the welcome modal.")
            time.sleep(1)
        except TimeoutException:
            log("info", "Welcome modal not found, proceeding.")

    def login(self, account_name, account_creds):
        if self.current_account == account_name:
            return True
        if self.current_account is not None:
            self.logout()

        log("info", f"🔑 Attempting to log in with {account_name} account...")
        if not self.safe_get(self.portal_config["login_url"]):
            return False

        try:
            try:
                another_user_button_wait = WebDriverWait(self.driver, 5)
                another_user_button = another_user_button_wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//p[text()='Login as another user'] | //div[text()='Login as another user']",
                        )
                    )
                )
                another_user_button.click()
            except (TimeoutException, NoSuchElementException):
                pass  # Button not always present

            self.wait.until(
                EC.visibility_of_element_located(
                    (By.ID, self.portal_config["username_field_id"])
                )
            ).send_keys(account_creds["username"])
            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, self.portal_config["continue_after_username_xpath"])
                )
            ).click()
            self.wait.until(
                EC.visibility_of_element_located(
                    (By.ID, self.portal_config["password_field_id"])
                )
            ).send_keys(account_creds["password"])
            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, self.portal_config["continue_after_password_xpath"])
                )
            ).click()
            self.wait.until(EC.url_contains("https://merchant.grab.com/"))

            log("success", f"✅ Login successful for {account_name}.")
            self.current_account = account_name
            self.handle_welcome_modal()
            return True
        except (TimeoutException, NoSuchElementException) as e:
            log("error", f"❌ Error during login for {account_name}: {e}")
            self.current_account = None
            return False

    def logout(self):
        if self.current_account is None:
            return
        log("info", f"🔒 Logging out from {self.current_account} account...")
        self.safe_get(self.portal_config["logout_url"])
        time.sleep(3)
        self.current_account = None

    def quit(self):
        if self.driver:
            self.driver.quit()
