"""Base browser session class to centralize Selenium setup and helpers."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Tuple
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from utils.logging import log
from services.base.exceptions import ServiceError


class BaseBrowserSession(ABC):
    """Abstract Base Class for managing a browser session for web scraping."""

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
            self.current_account: Optional[str] = None
        except Exception as e:
            raise ServiceError("Browser initialization failed.") from e

    @abstractmethod
    def login(self, account_name: str, credentials: Dict[str, str]) -> bool:
        """Logs into the target service."""
        pass

    @abstractmethod
    def collect_data(self) -> Tuple[List[Dict[str, Any]], str]:
        """Collects data from the target service."""
        pass

    @abstractmethod
    def logout(self):
        """Logs out from the target service."""
        pass

    def quit(self):
        """Closes the browser and quits the driver."""
        if self.driver:
            log("info", "Closing browser.")
            self.driver.quit()
            raise BrowserError(f"Unexpected error during browser setup: {e}")

    def teardown(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            self.logger.warning(f"Error during browser teardown: {e}")
        finally:
            self.driver = None

    def safe_get(self, url: str) -> bool:
        """Navigates to a URL with a try-except block for timeouts."""
        try:
            self.driver.get(url)
            return True
        except TimeoutException:
            self.logger.error(
                f"Page took too long to load and timed out: {url}")
            raise BrowserError(f"Timeout loading page: {url}")
        except WebDriverException as e:
            self.logger.error(f"WebDriver error navigating to {url}: {e.msg}")
            raise BrowserError(f"WebDriver error on get: {e.msg}")

    def handle_generic_popups(self):
        """Looks for common pop-ups (like cookie banners) and closes them."""
        try:
            cookie_button_xpath = "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]"
            short_wait = WebDriverWait(self.driver, 6)
            cookie_button = short_wait.until(
                EC.element_to_be_clickable((By.XPATH, cookie_button_xpath)))
            cookie_button.click()
            self.logger.info("   Closed a generic pop-up/cookie banner.")
        except (TimeoutException, NoSuchElementException):
            pass

    @abstractmethod
    def login(self, account_name: str, credentials: Dict[str, str]) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def collect_data(self) -> Optional[List[Dict[str, Any]]]:
        raise NotImplementedError()

    def __enter__(self):
        self.setup_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.teardown()
