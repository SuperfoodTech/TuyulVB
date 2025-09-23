"""Base browser session class to centralize Selenium setup and helpers."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from ..base.exceptions import BrowserError


class BaseBrowserSession(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.current_account: Optional[str] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def setup_driver(self, headless: bool = True):
        self.logger.info("🚀 Initializing browser...")
        try:
            service = Service(ChromeDriverManager().install())
            options = webdriver.ChromeOptions()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument(
                '--disable-blink-features=AutomationControlled')

            selenium_wire_options = {'disable_encoding': True}

            self.driver = webdriver.Chrome(
                service=service,
                options=options,
                seleniumwire_options=selenium_wire_options
            )
            self.driver.set_page_load_timeout(60)
            self.wait = WebDriverWait(self.driver, 60)
            return self.driver
        except WebDriverException as e:
            self.logger.fatal(f"WebDriver initialization failed: {e.msg}")
            self.driver = None
            raise BrowserError(f"WebDriver initialization failed: {e.msg}")
        except Exception as e:
            self.logger.fatal(
                f"An unexpected error occurred during browser setup: {e}")
            self.driver = None
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
