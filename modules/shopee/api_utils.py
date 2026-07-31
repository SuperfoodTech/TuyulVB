import time
import os
import json
import base64
import requests
from typing import Tuple, Optional
from common.logger import get_logger

log = get_logger("shopee_api_utils")


# Project paths (not required for current logic but kept for compatibility)
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(current_dir, "..", ".."))
CACHE_DIR = os.path.join(PROJECT_ROOT, "data", "cache")
TOKEN_FILE = os.path.join(CACHE_DIR, "shopee_auth_tokens.json")

# API Configuration — updated to new Shopee Partner API base
SHOPEE_API_BASE = "https://api.partner.shopee.co.id/nb/mss"
SHOPEE_API_BASE_LEGACY = "https://foody.shopee.co.id"  # kept for compatibility
API_TIMEOUT = 10


def _decode_jwt_payload(jwt_str: str) -> dict:
    """Decode the payload of a JWT token (no signature verification)."""
    try:
        parts = jwt_str.split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return {}


def _extract_merchant_token_from_requests(driver) -> Tuple[Optional[str], Optional[str]]:
    """Extract X-Merchant-Token and entity_id from seleniumwire intercepted requests.

    The new Shopee Partner API uses `X-Merchant-Token: B:xxx` header instead of cookies.
    This function scans the most recent intercepted requests and returns the token.
    Returns (merchant_token, entity_id).
    """
    try:
        requests_list = getattr(driver, "requests", [])
        for req in reversed(requests_list):
            if req is None or not getattr(req, "url", None):
                continue
            if "api.partner.shopee.co.id" not in req.url:
                continue
            hdr = req.headers or {}
            # X-Merchant-Token contains the B:xxx tob_token
            merchant_token = hdr.get("X-Merchant-Token") or hdr.get("x-merchant-token", "")
            if merchant_token and merchant_token.startswith("B:"):
                # entity_id / userid from the JWT cookie
                entity_id = ""
                try:
                    for c in driver.get_cookies():
                        if c.get("name") == "__shopee_partner_website_x_token_live":
                            payload = _decode_jwt_payload(c["value"])
                            entity_id = str(payload.get("userid", ""))
                            break
                except Exception:
                    pass
                return merchant_token, entity_id
    except Exception as e:
        log.debug(f"Failed to extract X-Merchant-Token from requests: {e}")
    return None, None



def get_shopee_headers(
    tob_token: str, entity_id: str = "", base_cookies_dict: dict = None,
    jwt_token: str = ""
) -> dict:
    """Generate headers for Shopee Partner API requests.

    New API: uses `X-Merchant-Token: B:xxx` header (api.partner.shopee.co.id).
    Legacy: uses cookie-based auth (foody.shopee.co.id) — kept for backward compat.
    """
    # New auth scheme: X-Merchant-Token header
    if tob_token and tob_token.startswith("B:"):
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "X-Merchant-Token": tob_token,
            "X-Merchant-ToB-ClientId": "undefined",
            "DNT": "1",
            "Origin": "https://partner.shopee.co.id",
            "Referer": "https://partner.shopee.co.id/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        }

    # Legacy auth scheme: cookie-based (foody.shopee.co.id)
    if base_cookies_dict:
        cookies = base_cookies_dict.copy()
        if jwt_token:
            cookies["__shopee_partner_website_x_token_live"] = jwt_token
        else:
            cookies["shopee_tob_entity_id"] = entity_id
            cookies["shopee_tob_token"] = tob_token
        cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    elif jwt_token:
        cookie_header = f"__shopee_partner_website_x_token_live={jwt_token}"
    else:
        cookie_header = f"shopee_tob_entity_id={entity_id}; shopee_tob_token={tob_token}"

    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/json",
        "Cookie": cookie_header,
        "DNT": "1",
        "Origin": "https://partner.shopee.co.id",
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

    # New API endpoint for token validation
    if tob_token.startswith("B:"):
        url = f"https://api.partner.shopee.co.id/nb/mss/web-api/PartnerAccountServer/GetUserInfo"
        try:
            response = requests.post(url, json={}, headers=headers, timeout=API_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                if data.get("error_code", 1) == 0:
                    log.debug("Token is valid (new API).")
                    return True
                log.warning(f"Token validation failed (new API). Code: {data.get('error_code')}")
                return False
        except Exception as e:
            log.warning(f"Token validation request failed (new API): {e}")
        return False

    # Legacy foody.shopee.co.id validation
    url = f"{SHOPEE_API_BASE_LEGACY}/api/seller/stores/search"
    payload = {"filter": {}, "page_no": 1, "page_size": 1}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)
        if response.status_code == 200 and response.json().get("code") == 0:
            log.debug("Token is valid (legacy API).")
            return True
        log.warning(f"Token validation failed (legacy). Code: {response.json().get('code')}")
    except Exception as e:
        log.warning(f"Token validation request failed (legacy): {e}")
    return False


# ---------------------------------------------------------------------------
# Browser cookie extraction helpers (previously in auth_utils)
# ---------------------------------------------------------------------------


def _parse_cookie_string(cookie_str: str) -> dict:
    """Parse a `Cookie: ...` header string into a dict."""
    result = {}
    for part in cookie_str.split(";"):
        kv = part.strip().split("=", 1)
        if len(kv) == 2:
            result[kv[0].strip()] = kv[1].strip()
    return result


def extract_tokens_from_driver(driver) -> Tuple[Optional[str], Optional[str]]:
    """Extract auth token and entity_id from a Selenium driver.

    Strategy 1 (primary): Scan seleniumwire intercepted requests for `X-Merchant-Token` header
                          (new Shopee Partner API: api.partner.shopee.co.id).
    Strategy 2 (fallback): Browser cookies — JWT `__shopee_partner_website_x_token_live`
                           or legacy `shopee_tob_token`.

    Returns `(tob_token, entity_id)` where `tob_token` is `B:xxx` (new) or legacy cookie value.
    """
    # Strategy 1: X-Merchant-Token from intercepted requests (most reliable)
    tob_token, entity_id = _extract_merchant_token_from_requests(driver)
    if tob_token:
        return tob_token, entity_id

    tob_token = None
    entity_id = None
    jwt_token = None

    # Strategy 2: Browser cookies — prefer new JWT cookie
    try:
        for c in driver.get_cookies():
            name = c.get("name", "")
            val = c.get("value", "")
            if name == "__shopee_partner_website_x_token_live" and val:
                jwt_token = val
            elif name == "shopee_tob_token" and val:
                tob_token = val
            elif name == "shopee_tob_entity_id" and val:
                entity_id = val
    except Exception:
        pass

    # Decode embedded token from JWT payload
    if jwt_token and not tob_token:
        payload = _decode_jwt_payload(jwt_token)
        raw_token = payload.get("token", "")
        if raw_token:
            tob_token = raw_token  # B:xxx format from JWT payload
            entity_id = entity_id or str(payload.get("userid", ""))
            log.info("tob_token extracted from JWT cookie payload.")

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

    # Shopee Partner pages known to set shopee_tob_token cookie
    CANDIDATE_PAGES = [
        "https://partner.shopee.co.id/settings/shopee-food/business-hours-settings",
        "https://partner.shopee.co.id/food/dashboard",
        "https://partner.shopee.co.id/",
    ]

    def _wait_for_token(max_wait: int = 15) -> Tuple[Optional[str], Optional[str]]:
        """Poll cookies every second until tob_token appears or timeout."""
        for _ in range(max_wait):
            tok, eid = extract_tokens_from_driver(driver)
            if tok:
                return tok, eid
            time.sleep(1)
        return None, None

    # Step 1: check current cookies first (token may already be present)
    tob_token, entity_id = extract_tokens_from_driver(driver)

    # Step 2: navigate through candidate pages until token found
    if not tob_token:
        log.warning("tob_token not found in cookies. Navigating through Shopee Partner pages to trigger Shopee Food API requests...")
        for page_url in CANDIDATE_PAGES:
            try:
                current = driver.current_url
                if page_url not in current:
                    # Clear past requests before navigating so we get fresh intercepts
                    try:
                        del driver.requests
                    except Exception:
                        pass
                    driver.get(page_url)
                tob_token, entity_id = _wait_for_token(max_wait=15)
                if tob_token:
                    log.info(f"tob_token extracted after navigating to: {page_url}")
                    break
                # If redirected to login, stop navigating — needs fresh manual login
                if "/login" in driver.current_url or "/authenticate" in driver.current_url:
                    log.warning("Redirected to Shopee login page — chromeprofile session may be expired.")
                    break
            except Exception as e:
                log.warning(f"Navigation to {page_url} failed: {e}")

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
