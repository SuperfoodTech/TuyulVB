import os
import random
import shutil
from datetime import datetime

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
try:
    from config.credentials_shopee import ACCOUNT_CREDS
except ImportError:
    ACCOUNT_CREDS = {}
from selenium.webdriver.chrome.service import Service
from types import SimpleNamespace
import time
from common.logger import get_logger

# Use the centralized logger
log = get_logger("browser_session")
log.propagate = False


def human_like_typing(element, text):
    """Types a string character by character with random delays to mimic human behavior."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.07, 0.2))


def request_interceptor(request):
    """A custom interceptor to log only the requests relevant for data extraction."""
    api_endpoints_to_log = [
        # "api/seller/stores/search",
        # "PartnerServer/GetStoreList",
        # "PartnerTransactionServer/GetTransactionList",
        # "api/seller/mis/orders/",
    ]
    if any(endpoint in request.url for endpoint in api_endpoints_to_log):
        log.info(f"Intercepted data request: {request.url}")


class BrowserSession:
    def __init__(self, headless=True):
        log.info("🚀 Initializing stealth browser session...")
        self.headless = headless
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--log-level=3")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            if headless:
                options.add_argument("--headless")
                options.add_argument("--window-size=1920,1080")
            else:
                options.add_argument("--start-maximized")
            options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
            script_dir = os.path.dirname(os.path.abspath(__file__))
            base_profiles_dir = os.path.join(script_dir, "selenium_profiles")
            profile_name = os.environ.get("SHOPEE_SELENIUM_PROFILE", "shopee_profile")
            profile_path = os.path.join(base_profiles_dir, profile_name)
            os.makedirs(profile_path, exist_ok=True)
            profile_path = os.path.abspath(profile_path)
            options.add_argument(f"--user-data-dir={profile_path}")
            # Also provide a profile-directory name to be explicit
            options.add_argument(f"--profile-directory={profile_name}")
            # Disable browser-side caching to avoid stale data and minimize disk usage
            options.add_argument("--disable-application-cache")
            options.add_argument("--disk-cache-size=0")
            # Configure selenium-wire / mitmproxy options to improve stability
            # Use an object (SimpleNamespace) because some selenium-wire
            # internals access option attributes rather than dict keys.
            seleniumwire_options = SimpleNamespace(
                verify_ssl=False,  # don't verify Shopee's cert via mitmproxy
                suppress_connection_errors=True,  # hide handshake failures
                disable_encoding=True,  # prevent gzip/encoding issues
                mitm_http2=False,  # CRITICAL: force HTTP/1.1 (disable HTTP/2)
            )
            # Try to construct a selenium-wire options object if available
            SWOptionsClass = None
            try:
                # selenium-wire exposed options class may live in different modules
                from seleniumwire.options import SeleniumWireOptions as SWOptionsClass  # type: ignore
            except Exception:
                try:
                    from seleniumwire.utils import SeleniumWireOptions as SWOptionsClass  # type: ignore
                except Exception:
                    SWOptionsClass = None

            driver_init_error = None

            def _init_driver(driver_cls, opts, sw_opts=None):
                # Try built-in Selenium Manager first (supports system Chrome/Chromium v149+)
                try:
                    kwargs = {"options": opts}
                    if sw_opts is not None:
                        kwargs["seleniumwire_options"] = sw_opts
                    return driver_cls(**kwargs)
                except Exception as ex1:
                    log.warning(f"Selenium Manager init failed ({ex1}), falling back to ChromeDriverManager...")
                    kwargs = {
                        "service": Service(ChromeDriverManager().install()),
                        "options": opts,
                    }
                    if sw_opts is not None:
                        kwargs["seleniumwire_options"] = sw_opts
                    return driver_cls(**kwargs)

            # Attempt 1: use SeleniumWireOptions class if available
            if SWOptionsClass:
                try:
                    sw_opts = SWOptionsClass(
                        {
                            "verify_ssl": False,
                            "suppress_connection_errors": True,
                            "disable_encoding": True,
                            "mitm_http2": False,
                        }
                    )
                    log.info("Initializing Chrome with SeleniumWireOptions instance")
                    self.driver = _init_driver(webdriver.Chrome, options, sw_opts)
                except Exception as e:
                    driver_init_error = e

            # Attempt 2: fallback to passing a plain dict (recommended by selenium-wire docs)
            if not getattr(self, "driver", None):
                try:
                    sw_opts_dict = {
                        "verify_ssl": False,
                        "suppress_connection_errors": True,
                        "disable_encoding": True,
                        "mitm_http2": False,
                    }
                    self.driver = _init_driver(webdriver.Chrome, options, sw_opts_dict)
                except Exception as e:
                    driver_init_error = e

            # Attempt 3: as a last resort, initialize plain selenium webdriver (no selenium-wire)
            if not getattr(self, "driver", None):
                try:
                    from selenium import webdriver as plain_webdriver  # type: ignore

                    self.driver = _init_driver(plain_webdriver.Chrome, options, None)
                except Exception as e:
                    driver_init_error = e

            if not getattr(self, "driver", None) and driver_init_error:
                raise driver_init_error

            # Set the custom interceptor to filter logs
            self.driver.request_interceptor = request_interceptor

            self.driver.set_page_load_timeout(60)  # Set page load timeout
            self.wait = WebDriverWait(self.driver, 30)
            self.current_account = None
        except Exception as e:
            log.critical(f"Failed to initialize browser session: {e}")
            self.driver = None

    def ensure_logged_in(self):
        """
        Checks if the current page is the login page, and if so, attempts to re-login.
        This is useful to call before navigating to a page that requires authentication.
        """
        try:
            current_url = self.driver.current_url
            if "/authenticate/login" in current_url:
                log.warning(
                    "  Session expired or redirected to login page. Attempting to re-login..."
                )
                # Get the master account from credentials to re-login
                master_account_name = list(ACCOUNT_CREDS.keys())[0]
                creds = ACCOUNT_CREDS[master_account_name]
                return self.login(master_account_name, creds)
            return True  # Already logged in
        except Exception as e:
            log.error(f"  An error occurred during login check: {e}")
            return False

    def login(self, account_name, creds):
        if self.current_account == account_name:
            return True
        log.info(f"🔑 Attempting to log in with master account '{account_name}'...")
        # Navigate to the dashboard first. If not logged in, it will redirect to the login page.
        self.driver.get("https://partner.shopee.co.id/food/dashboard")
        try:
            time.sleep(random.uniform(2.0, 4.0))
            # If we are already on the dashboard, login is considered successful.
            if "/food/dashboard" in self.driver.current_url:
                log.info("  Already on the dashboard. Login successful.")
                return True
            if "/food/dashboard" not in self.driver.current_url:
                # If we are on a login page, perform the login.
                if "/login" in self.driver.current_url:
                    log.info("  ➡️ Beginning human-like login interaction...")

                    if creds.get("phone"):
                        log.info(f"  Login using Phone Number: {creds.get('phone')}")
                        # Click 'Log in dengan no. HP'
                        log.info("  Clicking 'Log in dengan no. HP' link...")
                        phone_login_link = self.wait.until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "//a[contains(text(), 'Log in dengan no. HP')]",
                                )
                            )
                        )
                        phone_login_link.click()
                        time.sleep(random.uniform(1.0, 2.0))

                        # Input Phone
                        log.info("  Entering phone number...")
                        phone_input = self.wait.until(
                            EC.visibility_of_element_located(
                                (By.CSS_SELECTOR, "input[type='tel']")
                            )
                        )
                        ActionChains(self.driver).move_to_element(
                            phone_input
                        ).click().perform()
                        time.sleep(random.uniform(0.5, 1.0))
                        # phone_input.clear() # Sometimes clear() triggers validation errors if empty, use with caution or backspace
                        phone_input.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                        human_like_typing(phone_input, creds["phone"])
                        time.sleep(random.uniform(0.8, 1.5))

                        # Click 'Selanjutnya'
                        log.info("  Clicking 'Selanjutnya'...")
                        next_button = self.wait.until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//button[contains(., 'Selanjutnya')]")
                            )
                        )
                        next_button.click()

                    else:
                        username_field = self.wait.until(
                            EC.visibility_of_element_located(
                                (
                                    By.CSS_SELECTOR,
                                    'input[placeholder="No. handphone / Username / Email"]',
                                )
                            )
                        )
                        password_field = self.wait.until(
                            EC.visibility_of_element_located(
                                (By.CSS_SELECTOR, 'input[placeholder="Password"]')
                            )
                        )
                        ActionChains(self.driver).move_to_element(
                            username_field
                        ).click().perform()
                        time.sleep(random.uniform(0.5, 1.0))
                        username_field.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                        human_like_typing(username_field, creds["username"])
                        time.sleep(random.uniform(0.8, 1.5))
                        ActionChains(self.driver).move_to_element(
                            password_field
                        ).click().perform()
                        password_field.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                        human_like_typing(password_field, creds["password"])
                        time.sleep(random.uniform(1.0, 2.0))
                        self.wait.until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//button[contains(., 'Masuk')]")
                            )
                        ).click()
                        try:
                            time.sleep(random.uniform(0.5, 1.2))
                            WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable(
                                    (By.XPATH, "//button[contains(., 'Lanjutkan')]")
                                )
                            ).click()
                            log.info("  ➡️ Clicked optional 'Continue' button.")
                        except TimeoutException:
                            pass

            log.info("  Waiting for post-login page to settle...")
            time.sleep(random.uniform(3.0, 5.0))
            current_url = self.driver.current_url
            if "/authenticate/login" in current_url:
                log.error("  Login failed. Redirected back to the login page.")
                return False
            elif "/food/dashboard" in current_url:
                log.info("  Login complete. Landed directly on the dashboard.")
            else:
                try:
                    log.info(
                        "  Attempting to find and select initial merchant profile...",
                    )
                    merchant_profile = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, "div.listItem")
                        )
                    )
                    ActionChains(self.driver).move_to_element(merchant_profile).pause(
                        random.uniform(0.5, 1.0)
                    ).click().perform()
                except TimeoutException:
                    if "/food/dashboard" in self.driver.current_url:
                        log.info(
                            "  Merchant selection was not needed (redirected to dashboard).",
                        )
                    else:
                        log.error(
                            "  Could not find merchant list and not on dashboard. Login failed.",
                        )
                        return False
            log.info("  Final validation: confirming dashboard URL...")
            self.wait.until(EC.url_contains("/food/dashboard"))
            # Use a custom level for success if needed, or just INFO
            # For simplicity, we'll use INFO with an emoji.
            log.info(f"✅ Login successful for {account_name}.")
            self.current_account = account_name
            return True
        except (TimeoutException, NoSuchElementException) as e:
            log.error(f"❌ Error during login for {account_name}. Details: {e}")
            return False

    def quit(self):
        if self.driver:
            self.driver.quit()
