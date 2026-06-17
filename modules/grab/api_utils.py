"""API helper utilities for Grab (curl/header builders, cookie utilities, etc.)."""

import json
import os
from typing import Dict


def cookie_dict_to_string(d: Dict[str, str]) -> str:
    """Convert a cookie dict to a semicolon-separated header string.
    Example: {'a':'1', 'b':'2'} -> 'a=1; b=2'
    """
    parts = []
    for k, v in d.items():
        if v is None:
            v = ""
        parts.append(f"{k}={v}")
    return "; ".join(parts)


def cookie_string_to_dict(cookie_str: str) -> Dict[str, str]:
    """Convert a cookie header string into a dict.
    Example: 'a=1; b=2' -> {'a':'1', 'b':'2'}
    """
    if not cookie_str:
        return {}
    out: Dict[str, str] = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def parse_cookie_input(raw: str) -> str:
    """Parse cookie input which may be:
    - a JSON string representing a dict of cookie-name -> value
    - a path to a JSON file containing such a dict
    - already a cookie header string
    Returns a cookie header string or None.
    """
    if not raw:
        return None
    # Try path to JSON file first
    try:
        if os.path.exists(raw):
            with open(raw, "r", encoding="utf-8") as f:
                obj = json.load(f)
                if isinstance(obj, dict):
                    return cookie_dict_to_string(obj)
    except Exception:
        pass

    # Try parsing as JSON string
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return cookie_dict_to_string(obj)
    except Exception:
        pass

    # Fallback: assume it's already a cookie header string
    return raw


def build_headers_for_api(auth: Dict[str, str]) -> Dict[str, str]:
    """Build request headers for Grab API calls.

    Args:
        auth: Dictionary with 'cookies' (cookie header string) and optionally 'x-hydra-jwt'

    Returns:
        Dictionary of headers ready for requests.Session
    """
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "id",
        "origin": "https://food.grab.com",
        "referer": "https://food.grab.com/",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        ),
        "x-country-code": "ID",
        "x-gfc-country": "ID",
    }
    # Use x-hydra-jwt for hydra device/session tokens
    if auth.get("x-hydra-jwt"):
        headers["x-hydra-jwt"] = auth["x-hydra-jwt"]

    # Only use cookies as extracted from auth/cookies
    cookie_str = auth.get("cookies") or ""
    cookie_dict = cookie_string_to_dict(cookie_str)
    headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookie_dict.items())
    return headers


def build_headers(cookie_dict: Dict[str, str]) -> str:
    """Return a curl command string for the catalog-stores endpoint using provided cookies."""
    cookie_header = cookie_dict_to_string(cookie_dict)
    curl = (
        "curl 'https://portal.grab.com/foodtroy/v1/ID/merchant-groups/catalog-stores?offset=0&limit=100&isWithItemPhotoCount=true' \\\n"
        f"  -H 'accept: application/json' \\ \n"
        f"  -H 'accept-language: en' \\ \n"
        f"  -b '{cookie_header}' \\ \n"
        "  -H 'dnt: 1' \\ \n"
        "  -H 'origin: https://merchant.grab.com' \\ \n"
        "  -H 'priority: u=1, i' \\ \n"
        "  -H 'referer: https://merchant.grab.com/' \\ \n"
        "  -H 'requestsource: troyPortal' \\ \n"
        '  -H \'sec-ch-ua: "Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"\' \\ \n'
        "  -H 'sec-ch-ua-mobile: ?0' \\ \n"
        "  -H 'sec-ch-ua-platform: \"Windows\"' \\ \n"
        "  -H 'sec-fetch-dest: empty' \\ \n"
        "  -H 'sec-fetch-mode: cors' \\ \n"
        "  -H 'sec-fetch-site: same-site' \\ \n"
        "  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'"
    )
    return curl
