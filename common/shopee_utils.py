import time
import random
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from common.logger import get_logger
from common.http_utils import parse_response_json

# Use the centralized logger
log = get_logger("shopee_utils")

# API Configuration
PARTNER_API_BASE = "https://api.partner.shopee.co.id/nb/mss/web-api"
# Primary endpoint
GET_USER_INFO_ENDPOINT = f"{PARTNER_API_BASE}/PartnerAccountServer/GetUserInfo"
# Fallback endpoints to try if primary fails
GET_STORE_LIST_ENDPOINT = f"{PARTNER_API_BASE}/PartnerServer/GetStoreList"
API_TIMEOUT = 10


def get_current_merchant_via_api(driver):
    """Get current merchant info via API (NO UI DEPENDENCY!).

    Uses the Partner API to retrieve merchant information.
    This executes a fetch() call inside the browser context, ensuring
    perfect header/cookie alignment with the active session.

    Args:
        driver: Selenium WebDriver instance

    Returns:
        dict: Merchant info including merchantName, merchantId, store_id
        None: If API call fails
    """
    try:
        log.info("📡 Fetching current merchant info via API (browser context)...")

        # Give browser a moment to load/settle
        time.sleep(2)

        # JavaScript to execute fetch in the browser context
        # This bypasses the need to manually reconstruct headers/cookies in Python
        fetch_script = """
        var callback = arguments[arguments.length - 1];
        var url = arguments[0];
        
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
                // Cookies are automatically sent by the browser
            },
            body: '{}'
        })
        .then(response => {
            if (!response.ok) {
                callback({error: 'HTTP error ' + response.status});
                return;
            }
            return response.json();
        })
        .then(data => callback(data))
        .catch(error => callback({error: error.toString()}));
        """

        # Execute the script
        try:
            # Set a script timeout just in case
            driver.set_script_timeout(15)
            response_data = driver.execute_async_script(
                fetch_script, GET_USER_INFO_ENDPOINT
            )
        except Exception as e:
            log.error(f"Failed to execute fetch script: {e}")
            return None

        # Log full response for debugging
        # log.debug(f"📝 Full API response: {response_data}")

        if not response_data:
            log.warning("Empty response from fetch script")
            return None

        if "error" in response_data:
            log.warning(f"API fetch error: {response_data['error']}")
            return None

        # Parse response
        data = response_data
        if data.get("errorCode") == 0 and "data" in data:
            merchant_info = data["data"]
            merchant_name = merchant_info.get("merchantName")
            merchant_id = merchant_info.get("merchantId")
            store_id = merchant_info.get("store_id")

            log.info(
                f"✅ Current merchant (via API): {merchant_name} (ID: {merchant_id}, Store: {store_id})"
            )
            return {
                "merchantName": merchant_name,
                "merchantId": merchant_id,
                "store_id": store_id,
                "full_response": merchant_info,
            }
        else:
            error_code = data.get("errorCode")
            error_msg = data.get("errorMsg", "Unknown error")
            log.debug(f"API returned error (code {error_code}): {error_msg}")
            return None

    except Exception as e:
        log.debug(f"Failed to get merchant info: {e}")
        return None


def validate_current_merchant(driver, expected_merchant_name: str) -> bool:
    """Validate that the current merchant matches the expected one.

    Attempts API validation first, but falls back to proven UI-based validation
    if API is unavailable (Partner API GetUserInfo endpoint doesn't exist yet).

    Args:
        driver: Selenium WebDriver instance
        expected_merchant_name: The merchant name to validate against

    Returns:
        bool: True if current merchant matches expected, False otherwise
    """
    try:
        log.info(f"🔍 Validating merchant: {expected_merchant_name}")

        # Try API first (will likely return None since endpoint doesn't exist)
        current_merchant = get_current_merchant_via_api(driver)

        if current_merchant is not None:
            # API worked! Use it
            actual_name = current_merchant.get("merchantName", "").strip()
            expected_clean = expected_merchant_name.strip()

            if actual_name == expected_clean:
                log.info(f"✅ Merchant validation passed (via API): {actual_name}")
                return True
            else:
                log.error(
                    f"❌ Merchant mismatch! Expected: {expected_clean}, Got: {actual_name}"
                )
                return False
        else:
            # API unavailable - use proven UI-based validation instead
            log.debug(f"ℹ️  Using UI-based validation (API unavailable)")
            log.warning("UI validation fallback is currently disabled by user request.")
            return False

    except Exception as e:
        log.error(f"❌ Merchant validation error: {e}")
        return False


def validate_merchant_via_ui(driver, expected_merchant_name: str) -> bool:
    """Fallback: Validate merchant using UI elements (less reliable but proven to work).

    Args:
        driver: Selenium WebDriver
        expected_merchant_name: Expected merchant name

    Returns:
        bool: True if merchant name matches
    """
    try:
        log.info(f"🔍 Validating merchant via UI: {expected_merchant_name}")
        # Wait for the merchant name element
        wait = WebDriverWait(driver, 5)
        name_element = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//div[@class='merchantName']"))
        )
        actual_name = name_element.text.strip()

        if actual_name == expected_merchant_name.strip():
            log.info(f"✅ Merchant validation passed (via UI): {actual_name}")
            return True
        else:
            log.error(
                f"❌ Merchant mismatch! Expected: {expected_merchant_name}, Got: {actual_name}"
            )
            return False

    except TimeoutException:
        log.warning(f"⚠️  Could not find merchant name element on page")
        return False
    except Exception as e:
        log.error(f"❌ UI validation failed: {e}")
        return False


def get_current_merchant_name(driver, wait: WebDriverWait):
    """Gets the name of the currently active merchant from the dashboard."""
    try:
        wait.until(EC.url_contains("https://partner.shopee.co.id/food/dashboard"))
        name_element = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//div[@class='merchantName']"))
        )
        return name_element.text
    except (TimeoutException, NoSuchElementException):
        log.warning("Could not determine the current merchant name on the dashboard.")
        return None


def switch_merchant(driver, wait: WebDriverWait, merchant_info: dict):
    """Switches to a different merchant account via the UI.

    Uses 'driver.requests' (selenium-wire) to validate the switch by intercepting
    the 'GetUserInfo' response that occurs automatically.
    """
    log.info(
        f"--- Attempting to switch to merchant: {merchant_info['validate_name']} ---"
    )
    try:
        driver.get("https://partner.shopee.co.id/food/dashboard")
        time.sleep(random.uniform(2, 4))
        actions = ActionChains(driver)
        profile_menu = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "li[data-menu-id*='account']")
            )
        )
        actions.move_to_element(profile_menu).perform()
        time.sleep(random.uniform(0.5, 1))
        switch_merchant_menu = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//span[text()='Pilih Merchant Lain']")
            )
        )
        actions.move_to_element(switch_merchant_menu).perform()
        time.sleep(random.uniform(0.5, 1))
        target_merchant_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    f"//span[contains(@class, 'sc-dhKdcB') and text()='{merchant_info['click_name']}']",
                )
            )
        )

        # Clear requests BEFORE clicking to ensure we catch the NEW request
        try:
            del driver.requests
        except AttributeError:
            log.debug(
                "Driver does not support requests interception (not selenium-wire)."
            )

        target_merchant_button.click()
        log.info("  Validating merchant switch...")
        wait.until(EC.url_contains("https://partner.shopee.co.id/food/dashboard"))

        # --- Validation: Intercept GetUserInfo response ---
        # This mirrors the logic in force_open.py
        user_info_pattern = re.compile(r"PartnerAccountServer/GetUserInfo")
        max_retries = 10  # 10 * 1s = 10s timeout

        for i in range(max_retries):
            try:
                # Check requests in reverse order (newest first)
                if hasattr(driver, "requests"):
                    for request in reversed(driver.requests):
                        if request.url and user_info_pattern.search(request.url):
                            if request.response and request.response.body:
                                data = parse_response_json(request.response)

                                # Validate content
                                if (
                                    data
                                    and data.get("errorCode") == 0
                                    and "data" in data
                                ):
                                    actual_name = (
                                        data["data"].get("merchantName", "").strip()
                                    )
                                    expected_name = merchant_info[
                                        "validate_name"
                                    ].strip()

                                    if actual_name == expected_name:
                                        log.info(
                                            f"✅ Successfully switched to: {expected_name}."
                                        )
                                        return True
                                    else:
                                        # Use debug instead of error here, as we might have caught an old request
                                        # or a transitionary state if we weren't careful.
                                        log.debug(
                                            f"  Captured merchant: {actual_name}, Expected: {expected_name}"
                                        )
            except Exception as e:
                log.debug(f"  Error inspecting network requests: {e}")

            time.sleep(1)

        log.warning(
            "⚠️  Network interception timed out or failed. Falling back to active probe..."
        )

        # --- Fallback: Active Probe (Fetch) ---
        # If we missed the network event, use the robust fetch method we added earlier
        if validate_current_merchant(driver, merchant_info["validate_name"]):
            log.info(
                f"✅ Successfully switched to {merchant_info['validate_name']} (Verified via Probe)."
            )
            return True

        log.error(
            f"❌ Failed to confirm switch to {merchant_info['validate_name']} via API after retries."
        )
        return False
    except (TimeoutException, NoSuchElementException) as e:
        log.error(
            f"❌ Failed to switch to merchant {merchant_info['validate_name']}. Details: {e}",
        )
        return False
