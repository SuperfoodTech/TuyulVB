import time
import random
import os
import sys
import json
import shutil
import jwt
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configure path to allow imports from common/config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from common.logger import get_logger
from modules.grab.api_utils import (
    build_headers,
    cookie_string_to_dict,
    cookie_dict_to_string,
)

try:
    from config import settings_grab
    from config import credentials_grab
except ImportError:
    # Fallback or handling if config not found (mainly for testing isolation)
    settings_grab = None
    credentials_grab = None

logger = get_logger("grab_runner")

# --- Constants as requested ---
LOGIN_URL = "https://weblogin.grab.com/merchant/login?service_id=MEXUSERS&redirect=https%3A%2F%2Fmerchant.grab.com%2Fportal"
DASHBOARD_URL = "https://merchant.grab.com/dashboard"
LOGOUT_URL = "https://merchant.grab.com/profile/logout"
REQUIRED_COOKIE_NAMES = [
    "grabid-openid-authn-ck",
    "passenger_authn_token",
    "passenger_authn_token_jti",
]


def decode_jwt_token(token):
    try:
        # Decode without verification just to inspect payload
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        logger.error(f"Failed to decode JWT token: {e}")
        return None


def ensure_required_cookies_present(
    cookie_dict: Dict[str, str],
    context: str = "",
    required_keys: Optional[List[str]] = None,
) -> bool:
    """Validate that all required cookies are present in a cookie dict.

    Args:
        cookie_dict: Dictionary of cookie names to values
        context: Optional context string for logging (e.g., "browser cookie store")
        required_keys: Optional list of cookie names to check. Defaults to REQUIRED_COOKIE_NAMES.

    Returns:
        True if all required cookies present, False otherwise
    """
    keys_to_check = required_keys if required_keys is not None else REQUIRED_COOKIE_NAMES
    missing = [k for k in keys_to_check if not cookie_dict.get(k)]
    
    # Special check for sa_MEXUSERS if using default list (Merchant Portal context)
    if required_keys is None:
        has_sa_mexusers = any(k.startswith("sa_MEXUSERS_") for k in cookie_dict.keys())
        if not has_sa_mexusers:
            missing.append("sa_MEXUSERS_ (any)")

    if missing:
        logger.error(
            "Missing required cookies (%s) in %s. Cookies present: %s",
            ", ".join(missing),
            context or "cookies",
            list(cookie_dict.keys()),
        )
        return False
    logger.debug("All required cookies present in %s", context or "cookies")
    return True


def extract_cookies_and_token(
    driver, timeout: int = 120, required_cookies: Optional[List[str]] = None
) -> tuple:
    """Extract cookies and hydra_device_token from an authenticated browser session.

    Polls the browser for required cookies in the selenium cookie store and
    hydra_device_token in sessionStorage, with a timeout.

    Args:
        driver: Selenium webdriver instance
        timeout: Maximum seconds to wait for required cookies (default 120)
        required_cookies: Optional list of cookie names to check. Defaults to REQUIRED_COOKIE_NAMES.

    Returns:
        Tuple of (cookie_header_string, hydra_token) or (None, None) if timeout
    """
    start = time.time()
    found_cookie = None
    found_token = None
    while time.time() - start < timeout:
        try:
            ready = driver.execute_script("return document.readyState")
        except Exception:
            ready = None
        # Try to get cookies from the browser cookie store (includes HttpOnly)
        try:
            selenium_cookies = driver.get_cookies() or []
            cookie_str_from_store = "; ".join(
                f"{c.get('name')}={c.get('value','')}" for c in selenium_cookies
            )
        except Exception:
            selenium_cookies = []
            cookie_str_from_store = ""
        # Also read document.cookie (excludes HttpOnly)
        try:
            cookie_str = driver.execute_script("return document.cookie || ''")
        except Exception:
            cookie_str = ""
        try:
            token = driver.execute_script(
                "return window.sessionStorage.getItem('hydra_device_token') || null"
            )
        except Exception:
            token = None

        # Process sa_MEXUSERS cookies
        try:
            sa_cookies = [
                c
                for c in selenium_cookies
                if c.get("name", "").startswith("sa_MEXUSERS_")
            ]
            if sa_cookies:
                # Find the latest one. Assuming no explicit timestamp in name, we might just take the last one or try to infer.
                # Since we don't have creation time, we'll iterate all or just pick one.
                # Let's pick the last one in the list as a heuristic or check all.
                latest_sa_cookie = sa_cookies[-1]
                logger.info(
                    f"Found sa_MEXUSERS cookie: {latest_sa_cookie.get('name')}"
                )
                decoded_val = decode_jwt_token(latest_sa_cookie.get("value"))
                if decoded_val:
                    logger.info(f"Decoded sa_MEXUSERS payload: {decoded_val}")
        except Exception as e:
            logger.warning(f"Error processing sa_MEXUSERS cookies: {e}")

        # Prefer cookie store (captures HttpOnly); fall back to document.cookie
        parsed_store = cookie_string_to_dict(cookie_str_from_store or "")
        parsed_doc = cookie_string_to_dict(cookie_str or "")
        present_store = list(parsed_store.keys())
        present_doc = list(parsed_doc.keys())
        logger.debug(
            "extract_cookies_and_token: ready=%s store_cookies=%s doc_cookies=%s token_present=%s",
            ready,
            present_store,
            present_doc,
            bool(token),
        )

        # Accept when required cookies are present in the browser cookie store
        if parsed_store and ensure_required_cookies_present(
            parsed_store, "browser cookie store", required_keys=required_cookies
        ):
            found_cookie = cookie_str_from_store
            if token:
                found_token = token
            break

        # If store didn't have them, accept if document.cookie contains them (non-HttpOnly case)
        if parsed_doc and ensure_required_cookies_present(
            parsed_doc, "document.cookie", required_keys=required_cookies
        ):
            found_cookie = cookie_str
            if token:
                found_token = token
            break

        # otherwise keep waiting; prefer page fully loaded
        if ready != "complete":
            time.sleep(1)
            continue

        time.sleep(2)

    return found_cookie, found_token


def human_like_typing(element, text):
    """Types a string character by character with random delays to mimic human behavior."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.07, 0.2))


def _profile_dir(profile_name: Optional[str] = None) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_profiles_dir = os.path.join(script_dir, "selenium_profiles")
    if not profile_name:
        profile_name = os.environ.get("GRAB_SELENIUM_PROFILE", "grab_profile")
    profile_dir = os.path.join(base_profiles_dir, profile_name)
    os.makedirs(profile_dir, exist_ok=True)
    return os.path.abspath(profile_dir)


def launch_driver(headless: bool = False, profile_name: Optional[str] = None):
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    options.add_experimental_option("useAutomationExtension", False)

    if headless:
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")

    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )

    profile_dir = _profile_dir(profile_name)
    options.add_argument(f"--user-data-dir={profile_dir}")
    # Default profile directory name inside user-data-dir
    p_name = profile_name or os.environ.get("GRAB_SELENIUM_PROFILE", "grab_profile")
    options.add_argument(f"--profile-directory={p_name}")

    # Suppress logging
    try:
        devnull = os.devnull
    except Exception:
        devnull = "NUL"

    options.add_argument("--log-level=3")
    options.add_argument("--disable-logging")

    service = Service(log_path=devnull)
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def extract_cookies(driver) -> dict:
    cookies = {}
    try:
        selenium_cookies = driver.get_cookies()
        for c in selenium_cookies:
            name = c.get("name")
            # Return ALL cookies to ensure we don't miss any required by the API
            # if name in REQUIRED_COOKIE_NAMES or name.startswith("sa_MEXUSERS_"):
            cookies[name] = c.get("value")
    except Exception as e:
        logger.error(f"Error extracting cookies: {e}")
    return cookies


def login_to_portal(driver, username, password):
    """
    Handles the login flow:
    1. Navigate to LOGIN_URL
    2. Check for 'Login as another user'
    3. Enter Username -> Continue
    4. Enter Password -> Continue
    5. Wait for Dashboard
    """
    driver.get(LOGIN_URL)

    # 2. Check for 'Login as another user'
    try:
        # <div class="styles__rightContentContainer___1h_s5"><p class="styles__accountName___mpBRG">Login as another user</p></div>
        # Use XPath to target the text specifically, which is more reliable than just the container class
        switch_user_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//p[contains(text(), 'Login as another user')]")
            )
        )
        logger.info("Found 'Login as another user', clicking it...")
        switch_user_btn.click()
    except TimeoutException:
        # Not present, assume we are on the fresh login form or already logged out
        pass
    except Exception as e:
        logger.debug(f"Check for 'Login as another user' skipped: {e}")

    # 3. Enter Username
    try:
        # <input ... id="Username" ...>
        user_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "Username"))
        )
        logger.info(f"Entering username: {username}")
        user_input.click()
        time.sleep(0.5)
        user_input.clear()
        human_like_typing(user_input, username)

        # Click Continue (Username)
        # robust xpath for button with text "Continue"
        continue_btn_1 = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(@class, 'dui-btn') and .//span[text()='Continue']]",
                )
            )
        )
        continue_btn_1.click()

    except Exception as e:
        logger.error(f"Error entering username: {e}")
        return False

    # 4. Enter Password
    try:
        # <input ... id="password" ...>
        pass_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "password"))
        )
        logger.info("Entering password...")
        pass_input.click()
        time.sleep(0.5)
        pass_input.clear()
        human_like_typing(pass_input, password)

        # Click Continue (Password)
        continue_btn_2 = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(@class, 'dui-btn') and .//span[text()='Continue']]",
                )
            )
        )
        continue_btn_2.click()

    except Exception as e:
        logger.error(f"Error entering password: {e}")
        return False

    # 5. Wait for Dashboard
    try:
        # Check for DASHBOARD_URL and "Welcome!"
        WebDriverWait(driver, 15).until(EC.url_contains("dashboard"))
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//h2[contains(text(), 'Welcome!') or contains(text(), 'Selamat datang!')]",
                )
            )
        )
        # Wait a few extra seconds to validate login as requested
        time.sleep(3)
        return True
    except TimeoutException:
        logger.error("Timeout waiting for dashboard/welcome message.")
        return False
    except Exception as e:
        logger.error(f"Error waiting for dashboard: {e}")
        return False


def get_available_portals():
    """Reads credentials and settings to list available portals."""
    if not credentials_grab or not hasattr(credentials_grab, "ACCOUNT_CREDS"):
        print("Error: credentials_grab.ACCOUNT_CREDS not found.")
        return []

    creds_keys = list(credentials_grab.ACCOUNT_CREDS.keys())
    return creds_keys


def display_merchant_menu(all_portals):
    """Displays the menu for selecting which merchant(s) to process."""
    print("\n" + "=" * 70)
    logger.info("Please select a merchant to process:")
    print("  1. Run All Merchants")
    for i, portal in enumerate(all_portals):
        print(f"  {i+2}. {portal}")

    base_index = len(all_portals) + 2
    print("-" * 20)
    print(f"  {base_index}. Manual Login Setup")
    print(f"  {base_index + 1}. Reset Profile (Clear Session)")
    print(f"  {base_index + 2}. Exit to Main Menu")
    print("=" * 70)
    return base_index


def select_portals_interactive(available_portals: List[str]) -> List[str]:
    """
    Displays the interactive menu for portal selection.
    Handles 'Manual Login' and 'Reset Profile' internal loops.
    Returns a list of selected portals to process, or an empty list if exiting.
    """
    driver = None
    while True:
        base_index = display_merchant_menu(available_portals)

        try:
            choice_input = input(f"Enter number (1-{base_index + 2}): ").strip()
            if not choice_input:
                continue
            choice = int(choice_input)
        except ValueError:
            logger.error("Invalid input.")
            continue

        # Exit
        if choice == base_index + 2:
            logger.info("Exiting to Main Menu.")
            if driver:
                driver.quit()
            return []

        # Reset Profile
        elif choice == base_index + 1:
            if driver:
                logger.info("Closing active driver for profile reset...")
                driver.quit()
                driver = None

            profile_dir = _profile_dir()
            if os.path.exists(profile_dir):
                if input("  [WARNING] Delete profile folder? [y/N]: ").lower() == "y":
                    try:
                        shutil.rmtree(profile_dir)
                        logger.info("✅ Profile folder deleted.")
                    except Exception as e:
                        logger.error(f"Could not delete profile folder: {e}")
            else:
                logger.info("Profile folder does not exist.")
            continue

        # Manual Login
        elif choice == base_index:
            logger.info("Starting manual login setup...")
            if driver:
                driver.quit()

            driver = launch_driver(headless=False)
            driver.get(LOGIN_URL)
            logger.warning(
                "Please log in manually. Press Enter here when you are done..."
            )
            input()
            logger.info("Manual login complete. You can now select a task to run.")
            if driver:
                driver.quit()
                driver = None
            continue

        # Selection Logic
        selected_portals = []
        if choice == 1:
            selected_portals = available_portals
        elif 2 <= choice < base_index:
            selected_portals = [available_portals[choice - 2]]
        else:
            logger.error("Invalid choice.")
            continue

        logger.info(f"Selected portals: {selected_portals}")
        if driver:
            driver.quit()
        return selected_portals


def main():
    available = get_available_portals()
    if not available:
        logger.error("No portals available in credentials.")
        return

    selected_portals = select_portals_interactive(available)
    if not selected_portals:
        return

    driver = None
    try:
        if not driver:
            driver = launch_driver(headless=False)

        # Process Loop
        for i, portal in enumerate(selected_portals):
            creds = credentials_grab.ACCOUNT_CREDS.get(portal)
            if not creds:
                logger.error(f"No credentials found for {portal}")
                continue

            logger.info(f"Log Start Processing: {portal}")

            # Login
            logger.info(f"Login: {portal}")
            success = login_to_portal(driver, creds["username"], creds["password"])

            if success:
                logger.info(f"Scrapping Started: {portal}")

                # Retrieve cookies (optional usage)
                _ = extract_cookies(driver)

                # Check if we need to switch (Logout)
                if i < len(selected_portals) - 1:
                    logger.info(f"Logout to Switch to another Portals: {portal}")
                    driver.get(LOGOUT_URL)
                    time.sleep(2)  # Wait for logout to process
            else:
                logger.error(f"Failed to login to {portal}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
