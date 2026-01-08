"""
Shared utilities for Shopee Food API interactions (Synchronous).
Handles token extraction, caching, and validation to minimize Selenium usage.
"""

import time
import json
import os
import requests
from common.logger import get_logger

log = get_logger("shopee_api_utils")

# Determine project root to locate cache directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Assuming structure: project/modules/shopee/api_utils.py -> project/data/cache
PROJECT_ROOT = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
CACHE_DIR = os.path.join(PROJECT_ROOT, "data", "cache")
TOKEN_FILE = os.path.join(CACHE_DIR, "shopee_auth_tokens.json")

# API Configuration
SHOPEE_API_BASE = "https://foody.shopee.co.id"
API_TIMEOUT = 5


def get_shopee_headers(tob_token: str, entity_id: str) -> dict:
    """
    Generate headers for Shopee Food API requests.
    """
    return {
        "Host": "foody.shopee.co.id",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/json",
        "Cookie": f"shopee_tob_entity_id={entity_id}; shopee_tob_token={tob_token}",
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
    """
    Validates the token by making a lightweight API call.
    """
    log.debug("Validating cached Shopee token...")
    headers = get_shopee_headers(tob_token, entity_id)
    # Use a safe, read-only endpoint. Store search with limit 1 is usually safe.
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


def save_tokens(tob_token: str, entity_id: str):
    """Saves tokens to JSON cache."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            json.dump(
                {"shopee_tob_token": tob_token, "shopee_tob_entity_id": entity_id}, f
            )
        log.debug(f"Tokens saved to {TOKEN_FILE}")
    except Exception as e:
        log.error(f"Failed to save tokens: {e}")


def load_tokens():
    """Loads tokens from JSON cache."""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                return data.get("shopee_tob_token"), data.get("shopee_tob_entity_id")
        except Exception as e:
            log.warning(f"Failed to load token cache: {e}")
    return None, None


def extract_tokens_from_driver(driver):
    """
    Directly extracts tokens from current driver cookies without navigation or caching.
    Returns: (tob_token, entity_id)
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


def get_auth_tokens(driver=None):
    """
    Retrieves authentication tokens (tob_token, entity_id).

    Logic:
    1. Try to load from cache.
    2. Validate cached token.
    3. If valid, return it (Selenium not used).
    4. If invalid/missing and driver is provided, extract from browser.
    5. Save new token to cache.

    Args:
        driver: Selenium webdriver instance (optional). If None, only cache is checked.

    Returns:
        tuple: (tob_token, entity_id) or (None, None)
    """
    # 1. Try Cache
    tob_token, entity_id = load_tokens()

    if tob_token and entity_id:
        if validate_token(tob_token, entity_id):
            log.info("Using valid cached authentication tokens.")
            return tob_token, entity_id
        else:
            log.info("Cached token expired or invalid.")

    # 2. Extract from Browser (if driver available)
    if driver:
        log.info("Extracting fresh authentication tokens from browser...")

        # Navigate to ensure cookies are present
        if "business-hours-settings" not in driver.current_url:
            try:
                driver.get(
                    "https://partner.shopee.co.id/settings/shopee-food/business-hours-settings"
                )
                time.sleep(5)
            except Exception as e:
                log.warning(f"Navigation failed: {e}")

        tob_token, entity_id = extract_tokens_from_driver(driver)

        # Retry logic if token not found
        if not tob_token:
            log.warning("tob_token not found in cookies. Refreshing page...")
            try:
                driver.refresh()
                time.sleep(5)
                tob_token, entity_id = extract_tokens_from_driver(driver)
            except Exception as e:
                log.error(f"Error during refresh: {e}")

        if tob_token:
            log.info("Fresh tokens extracted successfully.")
            # Verify we have an entity_id, if not, try to save what we have or warn
            if not entity_id:
                log.warning(
                    "shopee_tob_entity_id not found in cookies. Saving token without it."
                )
                entity_id = ""  # Avoid None for file write

            save_tokens(tob_token, entity_id)
            return tob_token, entity_id
        else:
            log.error("Failed to extract tokens from browser.")

    else:
        log.warning("No valid cache and no driver provided. Cannot authenticate.")

    return None, None


# Backward compatibility alias (if needed, but better to update callers)
extract_auth_tokens = get_auth_tokens
