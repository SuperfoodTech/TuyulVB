import time
import os
import requests
from typing import Tuple, Optional
from common.logger import get_logger

log = get_logger("shopee_api_utils")


# Project paths (not required for current logic but kept for compatibility)
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(current_dir, "..", ".."))
CACHE_DIR = os.path.join(PROJECT_ROOT, "data", "cache")
TOKEN_FILE = os.path.join(CACHE_DIR, "shopee_auth_tokens.json")

# API Configuration
SHOPEE_API_BASE = "https://foody.shopee.co.id"
API_TIMEOUT = 5


def get_shopee_headers(
    tob_token: str, entity_id: str, base_cookies_dict: dict = None
) -> dict:
    """Generate headers for Shopee Food API requests."""

    if base_cookies_dict:
        # Use provided cookies and update specific auth fields
        cookies = base_cookies_dict.copy()
        cookies["shopee_tob_entity_id"] = entity_id
        cookies["shopee_tob_token"] = tob_token

        cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    else:
        # Fallback to minimal cookies
        cookie_header = (
            f"shopee_tob_entity_id={entity_id}; shopee_tob_token={tob_token}"
        )

    return {
        "Host": "foody.shopee.co.id",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/json",
        "Cookie": cookie_header,
        "DNT": "1",
        "Origin": "https://partner.shopee.co.id",
        "Priority": "u=1, i",
        "Referer": "https://partner.shopee.co.id/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "X-Sf-Platform": "2",
        "Operate-Source": "partnerapp",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    }


def validate_token(tob_token: str, entity_id: str) -> bool:
    """Validates the token by making a lightweight API call."""
    log.debug("Validating Shopee token...")
    headers = get_shopee_headers(tob_token, entity_id)
    url = f"{SHOPEE_API_BASE}/api/seller/stores/search"
    payload = {"filter": {}, "page_no": 1, "page_size": 1}

    try:
        response = requests.post(
            url, json=payload, headers=headers, timeout=API_TIMEOUT
        )
        if response.status_code == 200 and response.json().get("code") == 0:
            log.debug("Token is valid.")
            return True
        log.warning(f"Token validation failed. Code: {response.json().get('code')}")
    except Exception as e:
        log.warning(f"Token validation request failed: {e}")

    return False


# ---------------------------------------------------------------------------
# Browser cookie extraction helpers (previously in auth_utils)
# ---------------------------------------------------------------------------


def extract_tokens_from_driver(driver) -> Tuple[Optional[str], Optional[str]]:
    """Extract `shopee_tob_token` and `shopee_tob_entity_id` from a Selenium driver.

    Returns a tuple `(tob_token, entity_id)` where values may be `None` or empty
    strings if not found.
    """
    cookies = driver.get_cookies()
    tob_token = None
    entity_id = None

    for c in cookies:
        name = c.get("name")
        if name == "shopee_tob_token":
            tob_token = c.get("value")
        elif name == "shopee_tob_entity_id":
            entity_id = c.get("value")

    return tob_token, entity_id


def get_cookies_dict(driver) -> dict:
    """Extract all cookies from the driver as a dictionary."""
    if not driver:
        return {}
    return {c["name"]: c["value"] for c in driver.get_cookies()}


def get_auth_tokens(driver, merchant_name: str = None, return_json: bool = False):
    """Extract fresh authentication tokens from an active webdriver session.

    This helper centralizes token extraction and retry logic. It does NOT
    persist tokens; callers decide whether to cache them.
    """
    if driver is None:
        log.warning("get_auth_tokens called without a driver")
        if return_json:
            return None
        return None, None

    log.info("Extracting authentication tokens from browser...")
    try:
        if "business-hours-settings" not in driver.current_url:
            driver.get(
                "https://partner.shopee.co.id/settings/shopee-food/business-hours-settings"
            )
            time.sleep(10)
    except Exception as e:
        log.warning(f"Navigation failed: {e}")

    tob_token, entity_id = extract_tokens_from_driver(driver)

    # Retry once if token not found
    if not tob_token:
        log.warning("tob_token not found in cookies. Refreshing page and retrying...")
        try:
            driver.refresh()
            time.sleep(5)
            tob_token, entity_id = extract_tokens_from_driver(driver)
        except Exception as e:
            log.error(f"Error during refresh: {e}")

    if tob_token:
        log.info("Fresh tokens extracted successfully.")
        if not entity_id:
            log.warning(
                "shopee_tob_entity_id not found in cookies. Proceeding with empty entity_id."
            )
            entity_id = ""

        if return_json:
            return {
                "shopee_tob_token": tob_token,
                "shopee_tob_entity_id": entity_id,
                "merchant_name": merchant_name,
            }
        return tob_token, entity_id

    log.error("Failed to extract tokens from browser.")
    if return_json:
        return None
    return None, None
