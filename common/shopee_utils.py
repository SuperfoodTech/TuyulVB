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
from modules.shopee.api_utils import get_auth_tokens

# Use the centralized logger
log = get_logger("shopee_utils")

# API Configuration
PARTNER_API_BASE = "https://api.partner.shopee.co.id/nb/mss/web-api"
# Primary endpoint
GET_USER_INFO_ENDPOINT = f"{PARTNER_API_BASE}/PartnerAccountServer/GetUserInfo"
# Fallback endpoints to try if primary fails
GET_STORE_LIST_ENDPOINT = f"{PARTNER_API_BASE}/PartnerServer/GetStoreList"
API_TIMEOUT = 10


def get_current_merchant_via_api(driver, extra_headers: dict = None):
    try:
        log.info("📡 Fetching current merchant info via API (browser context)...")

        # Give browser a moment to load/settle
        time.sleep(3)

        # JavaScript to execute fetch in the browser context
        # Try multiple endpoints and methods, include credentials so cookies are sent,
        # and allow optional custom headers and POST body (useful to force GetUserInfo).
        fetch_script = """
        var callback = arguments[arguments.length - 1];
        var endpoints = arguments[0];

        function safeFetch(url, options) {
            // Append timestamp to prevent caching
            var cleanUrl = url + (url.indexOf('?') >= 0 ? '&' : '?') + '_ts=' + new Date().getTime();
            return fetch(cleanUrl, options)
            .then(function(response) {
                if (!response.ok) {
                    return {__fetch_error: 'HTTP ' + response.status, status: response.status};
                }
                return response.json().catch(function(e){ return {__fetch_error: 'invalid_json:'+e.toString()}; });
            })
            .catch(function(err) {
                return {__fetch_error: err.toString()};
            });
        }

        (async function(){
            var lastError = null;
            for (var i = 0; i < endpoints.length; i++){
                var entry = endpoints[i];
                var url = entry.url;
                var methods = entry.methods || ['POST','GET'];
                var headerOverrides = entry.headers || {};
                for (var m = 0; m < methods.length; m++){
                    var method = methods[m];
                    var opts = {
                        method: method,
                        headers: Object.assign({'Accept': 'application/json', 'Content-Type': 'application/json'}, headerOverrides),
                        credentials: 'include',
                        cache: 'no-store'
                    };
                    // For POST send an empty JSON body to emulate the curl sample
                    if (method === 'POST') {
                        opts.body = JSON.stringify(entry.body || {});
                    }

                    var res = await safeFetch(url, opts);
                    if (res && !res.__fetch_error){
                        callback({url: url, method: method, payload: res});
                        return;
                    }
                    lastError = {url: url, method: method, error: res && res.__fetch_error};
                }
            }
            callback({error: 'all_attempts_failed', lastError: lastError});
        })();
        """

        # Execute the script
        try:
            # Set a script timeout just in case
            driver.set_script_timeout(20)
            # Prefer POST first (matches provided curl) and include any extra headers requested
            endpoints = [
                {
                    "url": GET_USER_INFO_ENDPOINT,
                    "methods": ["POST", "GET"],
                    "headers": (extra_headers or {}),
                    "body": {},
                },
                {
                    "url": GET_STORE_LIST_ENDPOINT,
                    "methods": ["POST", "GET"],
                    "headers": (extra_headers or {}),
                    "body": {},
                },
            ]
            response_data = driver.execute_async_script(fetch_script, endpoints)
        except Exception as e:
            log.error(f"Failed to execute fetch script: {e}")
            return None

        # Log full response for debugging
        # log.debug(f"📝 Full API response: {response_data}")

        if not response_data:
            log.warning("Empty response from fetch script")
            return None

        if "error" in response_data:
            log.warning(
                f"API fetch error: {response_data.get('error')} lastError={response_data.get('lastError')}"
            )
            return None

        # Parse response payload returned by the browser fetch script
        data = response_data.get("payload") if isinstance(response_data, dict) else None
        # If payload not present, maybe the script returned the JSON directly
        if (
            data is None
            and isinstance(response_data, dict)
            and "payload" not in response_data
        ):
            data = response_data
        if isinstance(data, dict) and data.get("errorCode") == 0 and "data" in data:
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
            # Try to be forgiving: sometimes the endpoint may return the merchant object directly
            if isinstance(data, dict) and any(
                k in data for k in ("merchantName", "merchantId")
            ):
                merchant_name = data.get("merchantName")
                merchant_id = data.get("merchantId")
                store_id = data.get("store_id") or data.get("storeId")
                return {
                    "merchantName": merchant_name,
                    "merchantId": merchant_id,
                    "store_id": store_id,
                    "full_response": data,
                }

            error_code = data.get("errorCode") if isinstance(data, dict) else None
            error_msg = (
                data.get("errorMsg", "Unknown error")
                if isinstance(data, dict)
                else str(data)
            )
            log.debug(f"API returned error (code {error_code}): {error_msg}")
            return None

    except Exception as e:
        log.debug(f"Failed to get merchant info: {e}")
        return None


def validate_current_merchant(driver, expected_merchant_name: str) -> bool:
    try:
        log.info(f"🔍 Validating merchant: {expected_merchant_name}")

        # Prefer an active POST probe to the GetUserInfo endpoint and use
        # get_auth_tokens to attach headers extracted from the browser session.
        tob_token, entity_id = get_auth_tokens(driver)

        probe_headers = None
        if tob_token:
            probe_headers = {
                "content-type": "application/json",
                "origin": "https://partner.shopee.co.id",
                "referer": "https://partner.shopee.co.id/",
                # attach merchant token so the active probe uses the same auth
                "x-merchant-token": tob_token,
            }
            if entity_id:
                probe_headers["x-merchant-from"] = str(entity_id)

        # Perform active probe via browser fetch (POST preferred inside helper)
        current_merchant = get_current_merchant_via_api(
            driver, extra_headers=probe_headers
        )

        if current_merchant is not None:
            actual_name = current_merchant.get("merchantName", "").strip()
            expected_clean = expected_merchant_name.strip()

            if actual_name.lower() == expected_clean.lower():
                log.info(f"✅ Merchant validation passed (via API): {actual_name}")
                return True
            else:
                log.error(
                    f"❌ Merchant mismatch! Expected: {expected_clean}, Got: {actual_name}"
                )
                return False

        # If API probe returned nothing, do not attempt UI validation here.
        log.debug(
            "API probe returned no result; merchant could not be validated via API"
        )
        return False
    except Exception as e:
        log.error(f"❌ Merchant validation error: {e}")
        return False


# Note: UI-based merchant validation removed — the code now relies on
# API-based validation via `get_current_merchant_via_api`.


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

        # Clear previous requests to ensure we capture fresh ones
        if hasattr(driver, "requests"):
            del driver.requests
        else:
            log.debug(
                "Driver does not support requests interception (not selenium-wire)."
            )

        target_merchant_button.click()
        log.info("  Validating merchant switch...")
        wait.until(EC.url_contains("https://partner.shopee.co.id/food/dashboard"))

        # Start listening immediately, don't sleep for 10s
        user_info_pattern = re.compile(r"PartnerAccountServer/GetUserInfo")
        max_retries = 5  # Poll for only 5 seconds (Fast Path)

        for i in range(max_retries):
            try:
                # Check requests in reverse order (newest first).
                if hasattr(driver, "requests"):
                    # Since we cleared requests before click, all requests are new
                    requests_snapshot = list(driver.requests)

                    found_any_match = False
                    for request in reversed(requests_snapshot):
                        try:
                            if request.url and user_info_pattern.search(request.url):
                                found_any_match = True
                                # Ensure response is available
                                resp = getattr(request, "response", None)
                                if not resp:
                                    log.debug(
                                        f"Matched URL but no response yet: {request.url}"
                                    )
                                    continue

                                # Log status code and body presence for diagnosis
                                status = getattr(resp, "status_code", None) or getattr(
                                    resp, "status", None
                                )
                                body = getattr(resp, "body", None)
                                body_len = len(body) if body is not None else 0

                                log.debug(
                                    f"Matched GetUserInfo response: status={status}, body_len={body_len}"
                                )

                                if body_len == 0:
                                    # Response present but empty body — skip
                                    log.debug(
                                        "Response body empty, continuing to next request."
                                    )
                                    continue

                                try:
                                    data = parse_response_json(resp)
                                except Exception as e:
                                    log.debug(f"Failed to parse response JSON: {e}")
                                    data = None

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

                                    # Case-insensitive comparison
                                    if actual_name.lower() == expected_name.lower():
                                        log.info(
                                            f"✅ Successfully switched to: {expected_name} (Captured Network Event)."
                                        )
                                        # Extract and cache tokens once for callers to reuse
                                        try:
                                            tob_token, entity_id = get_auth_tokens(
                                                driver
                                            )
                                            driver._shopee_auth = {
                                                "tob_token": tob_token,
                                                "entity_id": entity_id,
                                            }
                                        except Exception:
                                            # don't fail the switch if caching tokens fails
                                            driver._shopee_auth = {
                                                "tob_token": None,
                                                "entity_id": None,
                                            }
                                        return True
                                    else:
                                        log.debug(
                                            f"Captured merchant: '{actual_name}', Expected: '{expected_name}' (Mismatch)"
                                        )
                                        # Keep looking in case there's a newer request
                                        continue
                        except Exception as inner_e:
                            log.debug(f"Error inspecting specific request: {inner_e}")

                else:
                    log.debug(
                        "Driver has no 'requests' attribute; cannot inspect network requests."
                    )
            except Exception as e:
                log.debug(f"Error inspecting network requests: {e}")

            time.sleep(1)

        # Retrieve captured URLs for debugging context
        captured_urls = []
        if hasattr(driver, "requests"):
            captured_urls = [r.url for r in list(driver.requests)[-5:]]  # Last 5 URLs

        log.info(
            f"ℹ️  Network event not captured (might be cached). Last URLs: {captured_urls}"
        )
        log.info("👉 Triggering Active API Probe for validation...")

        # --- Fallback: Active Probe (Fetch) ---
        # If we missed the network event, actively POST to the GetUserInfo endpoint
        probe_headers = {
            "content-type": "application/json",
            "origin": "https://partner.shopee.co.id",
            "referer": "https://partner.shopee.co.id/",
        }
        # Attach x-merchant-token from browser session using central extractor
        tob_token, entity_id = get_auth_tokens(driver)
        if tob_token:
            probe_headers["x-merchant-token"] = tob_token
        # Prefer including the merchant/store id as x-merchant-from when available
        if merchant_info.get("store_id"):
            probe_headers["x-merchant-from"] = str(merchant_info.get("store_id"))
        elif merchant_info.get("merchantId"):
            probe_headers["x-merchant-from"] = str(merchant_info.get("merchantId"))

        probe_resp = get_current_merchant_via_api(driver, extra_headers=probe_headers)
        if probe_resp is not None:
            actual_name = probe_resp.get("merchantName", "").strip()
            expected_name = merchant_info["validate_name"].strip()
            if actual_name.lower() == expected_name.lower():
                log.info(
                    f"✅ Successfully switched to {expected_name} (Verified via Active Probe)."
                )
                # Cache tokens on the driver so callers can reuse and avoid re-extraction
                try:
                    driver._shopee_auth = {
                        "tob_token": tob_token,
                        "entity_id": entity_id,
                    }
                except Exception:
                    driver._shopee_auth = {"tob_token": None, "entity_id": None}
                return True
            else:
                log.debug(
                    f"Active probe returned merchant '{actual_name}' (expected '{expected_name}')."
                )
    except (TimeoutException, NoSuchElementException) as e:
        log.error(
            f"❌ Failed to switch to merchant {merchant_info['validate_name']}. Details: {e}",
        )
        return False
