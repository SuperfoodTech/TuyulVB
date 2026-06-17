import argparse
import json
import os
from datetime import datetime
from typing import Dict, List
import logging

import pandas as pd
import requests
import time
import random
from common import monday_utils
from common.logger import get_logger
from common.notifications import send_discord_file
from common.config import get_config
from modules.grab.api_utils import (
    cookie_string_to_dict,
    parse_cookie_input,
    build_headers_for_api,
)
from modules.grab.browser_session import (
    extract_cookies_and_token,
    ensure_required_cookies_present,
)

REQUIRED_CONSUMER_COOKIES = [
    "grabid-openid-authn-ck",
    "passenger_authn_token",
    "passenger_authn_token_jti",
]


DEFAULT_MERCHANTS = ["6-C7EHLGKXLLLKCE"]

DEFAULT_BRAND_MAPPING = {
    "Foodnesia": "text_mky9b8z9",
    "WonderFood": "text_mky974s9",
    "Lokarasa": "text_mky9pxvr",
    "DoEat": "text_mky9z4ts",
}


logger = get_logger("grab_menu_extract")


def fetch_merchant(
    session: requests.Session,
    merchant_id: str,
    headers: Dict[str, str],
    max_retries: int = 3,
) -> dict:
    """
    Fetch merchant JSON with retries, exponential backoff and jitter on 429/connection errors.
    """
    url = f"https://portal.grab.com/foodweb/guest/v2/merchants/{merchant_id}?latlng=-7.28573,112.65145"

    # Use a longer initial backoff to reduce tight retry loops (configurable via env)
    backoff = float(os.environ.get("GRAB_RETRY_BACKOFF_INITIAL", "5.0"))
    max_backoff = float(os.environ.get("GRAB_RETRY_BACKOFF_MAX", "120"))
    for attempt in range(1, max_retries + 1):
        try:
            logger.debug("GET %s (attempt %s)", url, attempt)
            resp = session.get(url, headers=headers, timeout=30)

            if resp.status_code == 429:
                # Respect Retry-After header if provided
                retry_after = resp.headers.get("Retry-After")
                try:
                    wait = (
                        float(retry_after)
                        if retry_after is not None
                        else backoff + random.uniform(0, backoff)
                    )
                except Exception:
                    wait = backoff + random.uniform(0, backoff)
                time.sleep(wait)
                backoff = min(backoff * 2, max_backoff)
                continue

            # If unauthorized or other errors, log response content (truncated) to help debugging
            if resp.status_code == 401:
                try:
                    logger.error(
                        "Unauthorized (401) fetching %s. Response headers: %s; body: %s",
                        url,
                        dict(resp.headers),
                        resp.text[:2000],
                    )
                except Exception:
                    logger.exception("Failed to log 401 response content")
                resp.raise_for_status()

            if resp.status_code >= 400:
                try:
                    logger.warning(
                        "HTTP %s fetching %s; body (truncated): %s",
                        resp.status_code,
                        url,
                        resp.text[:1000],
                    )
                except Exception:
                    logger.exception("Failed to log error response body")
                resp.raise_for_status()

            return resp.json()

        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                raise
            wait = backoff + random.uniform(0, backoff)
            logger.debug("Retrying after %.1fs (attempt %s)", wait, attempt + 1)
            time.sleep(wait)
            backoff = min(backoff * 2, max_backoff)
            continue


def detect_brand(merchant: dict) -> str:
    name = merchant.get("chainName") or merchant.get("name") or ""
    for keyword in DEFAULT_BRAND_MAPPING.keys():
        if keyword.lower() in name.lower():
            return keyword
    # fallback: try branchName
    branch = merchant.get("branchName", "")
    for keyword in DEFAULT_BRAND_MAPPING.keys():
        if keyword.lower() in branch.lower():
            return keyword
    return ""


def parse_menu(
    merchant_json: dict, brand_mapping: Dict[str, str], merchant_meta: Dict[str, str]
) -> List[dict]:
    merchant = merchant_json.get("merchant", {})
    menu = merchant.get("menu", {})
    categories = menu.get("categories", [])
    results = []

    brand = detect_brand(merchant)
    gr_sid_value = brand_mapping.get(brand, "")

    # lookup color value by merchant SID if provided
    merchant_id = merchant.get("ID", "")
    color_val = merchant_meta.get(merchant_id, "")

    for cat in categories:
        cat_name = cat.get("name")
        items = cat.get("items", [])
        for it in items:
            row = build_row(merchant, brand, gr_sid_value, cat_name, it, color_val)
            results.append(row)

        # handle elementCards if present
        for card in cat.get("elementCards", []):
            item = card.get("item")
            if item:
                row = build_row(
                    merchant, brand, gr_sid_value, cat_name, item, color_val
                )
                results.append(row)

    return results


def is_available_value(v) -> bool:
    """Normalize availability values from the scraped item.
    - True boolean => available
    - None or missing => not available
    - Accept common string/int truthy values: "true", "1", "yes", "available", "on"
    """
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in ("true", "1", "yes", "available", "on")


def build_row(
    merchant: dict,
    brand: str,
    gr_sid_value: str,
    category_name: str,
    item: dict,
    color_value: str,
) -> dict:
    # Helpers to safely extract nested numeric prices
    def safe_amount(dct, key_path: List[str]):
        cur = dct
        for k in key_path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(k)
            if cur is None:
                return None
        return cur

    price_minor = (
        safe_amount(item, ["priceV2", "amountInMinor"])
        or safe_amount(item, ["priceInMinorUnit"])
        or None
    )
    discounted_minor = (
        safe_amount(item, ["discountedPriceV2", "amountInMinor"])
        or safe_amount(item, ["discountedPriceInMin"])
        or None
    )

    # Normalise by dividing by 100 per instructions
    def norm(v):
        try:
            return float(v) / 100.0 if v is not None else None
        except Exception:
            return None

    fake_price_gr = norm(price_minor)
    gr_price = norm(discounted_minor)

    row = {
        "Fullname": merchant.get("name", ""),
        "Gr - SID": merchant.get("ID", ""),
        "Category": category_name,
        "Item": item.get("name", ""),
        "Description": item.get("description", ""),
        "Fake Price Gr": fake_price_gr,
        "Gr Price": gr_price,
        "Availability": "Yes" if is_available_value(item.get("available")) else "No",
        "Scale": color_value,
    }
    return row


def write_excel(rows: List[dict], output_file: str):
    df = pd.DataFrame(rows)
    df.sort_values(by=["Fullname", "Gr - SID", "Category", "Item"], inplace=True)

    # Write to excel and format currency for price columns
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        workbook = writer.book
        worksheet = writer.sheets["Sheet1"]

        # Attempt to format the two price columns as IDR currency
        try:
            from openpyxl.styles import numbers

            # find column letters
            for col_name in ["Fake Price Gr", "Gr Price"]:
                if col_name in df.columns:
                    col_idx = df.columns.get_loc(col_name) + 1
                    # openpyxl is 1-based and Excel header present -> start row 2
                    for row_idx in range(2, 2 + len(df)):
                        cell = worksheet.cell(row=row_idx, column=col_idx)
                        if isinstance(cell.value, (int, float)):
                            # Indonesian rupiah style
                            cell.number_format = "Rp#,##0.00"
        except Exception:
            pass


def interactive_mode_selection():
    """Display an interactive menu to let user choose between manual setup or auto-extract."""
    print("\n" + "=" * 70)
    print("GrabFood Menu Extraction Tool")
    print("=" * 70)
    print("\nPlease choose a mode to proceed:\n")
    print("  1. Extract")
    print("  2. Manual Setup")
    print("  3. Exit")
    print("\n" + "-" * 70)

    while True:
        try:
            choice = input("Enter your choice (1-3): ").strip()
            if choice == "1":
                return "auto_extract"
            elif choice == "2":
                return "setup"
            elif choice == "3":
                logger.info("User chose to exit.")
                return None
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        except KeyboardInterrupt:
            logger.info("User interrupted; exiting.")
            return None


def main():
    parser = argparse.ArgumentParser(description="Extract Grab merchant menu to Excel")
    parser.add_argument(
        "--output", "-o", default="Grabfood_menu.xlsx", help="Output Excel file"
    )
    parser.add_argument(
        "--merchant-ids",
        "-m",
        help="Comma separated merchant ids to fetch (default example merchant)",
    )
    parser.add_argument(
        "--auto-extract",
        action="store_true",
        help="Open Chrome and extract cookies + hydra_device_token from https://food.grab.com/id/id/ (requires selenium).",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Open Chrome for manual operation (no automation, just browser for user to login and inspect).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome in headless mode when auto-extracting.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging and verbose request/response output.",
    )

    parser.add_argument(
        "--brand-mapping",
        "-b",
        help=(
            "Optional JSON string or path to JSON file mapping brand->Gr-SID. "
            'Example: \'{"Foodnesia": "text_mky9b8z9"}\''
        ),
    )

    parser.add_argument(
        "--cookies",
        help="Cookie header string or path to JSON file containing cookie dict",
    )
    parser.add_argument(
        "--x-hydra-jwt",
        help="Hydra device JWT token (will be used as x-hydra-jwt header)",
    )
    parser.add_argument(
        "--x-hydra-token",
        help="Alternative hydra device token (alias for x-hydra-jwt)",
    )

    args = parser.parse_args()

    # Enable debug logging if requested
    if getattr(args, "debug", False):
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    # If no mode explicitly specified, show interactive menu
    if not args.setup and not args.auto_extract:
        mode = interactive_mode_selection()
        if mode is None:
            return
        if mode == "setup":
            args.setup = True
            args.auto_extract = False
            args.headless = False  # Manual setup: show browser UI
        elif mode == "auto_extract":
            args.setup = False
            args.auto_extract = True
            args.headless = True  # Auto-extract: run in headless mode by default

    if args.merchant_ids:
        merchant_ids = [s.strip() for s in args.merchant_ids.split(",") if s.strip()]
    else:
        merchant_ids = None

    # load mapping
    brand_mapping = DEFAULT_BRAND_MAPPING.copy()
    if args.brand_mapping:
        try:
            # try to parse as JSON first
            bm = json.loads(args.brand_mapping)
            if isinstance(bm, dict):
                brand_mapping.update(bm)
        except Exception:
            # try to open file
            try:
                with open(args.brand_mapping, "r", encoding="utf-8") as f:
                    bm = json.load(f)
                    if isinstance(bm, dict):
                        brand_mapping.update(bm)
            except Exception:
                logger.warning("Could not parse brand mapping; using defaults")

    # Collect authentication values from CLI or environment
    cookies_raw = (
        args.cookies or os.environ.get("GRAB_COOKIES") or os.environ.get("GRAB_COOKIE")
    )
    cookies = parse_cookie_input(cookies_raw)
    x_hydra_jwt = args.x_hydra_jwt or os.environ.get("GRAB_X_HYDRA_JWT")
    # Accept hydra device token from env/arg; use it as x-hydra-jwt
    hydra_device_token = (
        args.x_hydra_token
        or os.environ.get("GRAB_X_HYDRA_TOKEN")
        or os.environ.get("HYDRA_DEVICE_TOKEN")
    )

    if not cookies and not args.auto_extract and not args.setup:
        logger.error(
            "cookies must be provided via --cookies or GRAB_COOKIES env var (or enable auto-extract)."
        )
        return

    auth = {}
    # Prefer explicit x_hydra_jwt, otherwise use hydra_device_token
    if x_hydra_jwt:
        auth["x-hydra-jwt"] = x_hydra_jwt
    elif hydra_device_token:
        auth["x-hydra-jwt"] = hydra_device_token
    auth["cookies"] = cookies

    headers = build_headers_for_api(auth)

    # If cookies were provided via CLI/env, validate they contain required keys
    provided_cookie_dict = cookie_string_to_dict(auth.get("cookies") or "")
    if provided_cookie_dict:
        if not ensure_required_cookies_present(
            provided_cookie_dict,
            "initial provided cookies",
            required_keys=REQUIRED_CONSUMER_COOKIES,
        ):
            logger.error(
                "Aborting due to missing required cookies in provided cookie string."
            )
            return

    driver = None
    if args.setup:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
        except Exception:
            logger.error("Selenium not available. Install with: pip install selenium")
            return
        logger.info(
            "Launching Chrome for manual operation. You may login and inspect manually. Press CTRL+C to exit when done."
        )
        time.sleep(5)
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--start-maximized")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_profiles_dir = os.path.join(script_dir, "selenium_profiles")
        profile_name = os.environ.get("GRAB_SELENIUM_PROFILE", "grab_profile")
        profile_dir = os.path.join(base_profiles_dir, profile_name)
        os.makedirs(profile_dir, exist_ok=True)
        profile_dir = os.path.abspath(profile_dir)
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument(f"--profile-directory={profile_name}")
        driver = webdriver.Chrome(options=options)
        driver.get(
            "https://food.grab.com/id/id/restaurant/rm-palapa-masakan-padang-lontar-delivery/6-CZJDEZC1GEMJL6?"
        )
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Manual browser session ended by user.")
        try:
            driver.quit()
        except Exception:
            pass
        return
    if args.auto_extract:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
        except Exception:
            logger.error("Selenium not available. Install with: pip install selenium")
            return
        logger.info(
            "Launching Chrome to extract cookies/token. Please login if required."
        )
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        if args.headless:
            options.add_argument("--headless")
            options.add_argument("--window-size=1920,1080")
        else:
            options.add_argument("--start-maximized")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        # Use a module-local selenium_profiles directory and allow an
        # environment override so different automations don't share the
        # same profile unintentionally.
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_profiles_dir = os.path.join(script_dir, "selenium_profiles")
        profile_name = os.environ.get("GRAB_SELENIUM_PROFILE", "grab_profile")
        profile_dir = os.path.join(base_profiles_dir, profile_name)
        os.makedirs(profile_dir, exist_ok=True)
        profile_dir = os.path.abspath(profile_dir)
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument(f"--profile-directory={profile_name}")
        driver = webdriver.Chrome(options=options)
        driver.get(
            "https://food.grab.com/id/id/restaurant/rm-palapa-masakan-padang-lontar-delivery/6-CZJDEZC1GEMJL6?"
        )
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            time.sleep(2)

            # Check if already logged in by looking for the user icon
            is_logged_in = False
            try:
                # Look for the logged-in box/user icon
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "LoggedInBox___CoDLs")
                    )
                )
                logger.info("User appears to be already logged in (found LoggedInBox).")
                is_logged_in = True
            except Exception:
                # Not found, proceed to try clicking login button
                pass

            if not is_logged_in:
                logger.info("Attempting to click 'Masuk/Daftar' button...")
                try:
                    login_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.CLASS_NAME, "NotLoggedInBox___2ic3u")
                        )
                    )
                    login_btn.click()
                    logger.info("Clicked 'Masuk/Daftar' button.")
                    time.sleep(2)
                except Exception as e:
                    logger.warning(
                        "Could not click 'Masuk/Daftar' button (might be already logged in or not found): %s",
                        e,
                    )

            cookies, token = extract_cookies_and_token(
                driver, required_cookies=REQUIRED_CONSUMER_COOKIES
            )
            if cookies:
                auth["cookies"] = cookies
                logger.info("Extracted cookies from browser.")
            else:
                logger.warning(
                    "No cookies found in the browser session within timeout."
                )
            if token:
                auth["x-hydra-jwt"] = token
                logger.info("Extracted hydra_device_token and mapped to x-hydra-jwt.")
            else:
                logger.warning(
                    "No hydra_device_token found in sessionStorage within timeout."
                )
            headers = build_headers_for_api(auth)
            # Validate extracted cookies contain required keys
            extracted = cookie_string_to_dict(auth.get("cookies") or "")
            if not ensure_required_cookies_present(
                extracted, "auto-extract", required_keys=REQUIRED_CONSUMER_COOKIES
            ):
                # Keep the browser open for debugging when cookies are missing
                logger.error(
                    "Aborting due to missing required cookies from browser extraction."
                )
                if driver:
                    logger.info(
                        "Leaving Chrome open for inspection. Press Ctrl+C to close and quit the browser."
                    )
                    try:
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        logger.info("User requested to close browser; quitting driver.")
                        try:
                            driver.quit()
                        except Exception:
                            pass
                return

        except Exception as e:
            logger.error(f"Error during auto-extraction: {e}")
            if driver:
                driver.quit()
            return

    # Use a single session for connection pooling and to help with rate limits
    session = requests.Session()
    session.headers.update(headers)

    # If we have a cookie header string, also populate session.cookies for requests
    if auth.get("cookies"):
        try:
            cookie_dict = cookie_string_to_dict(auth.get("cookies") or "")
            if cookie_dict:
                session.cookies.update(cookie_dict)
                logger.debug("Session cookies set: %s", session.cookies.get_dict())
                # Validate required cookies after populating session
                if not ensure_required_cookies_present(
                    cookie_dict,
                    "session cookie setup",
                    required_keys=REQUIRED_CONSUMER_COOKIES,
                ):
                    logger.error(
                        "Aborting due to missing required cookies in session. Browser left open for inspection."
                    )
                    if driver:
                        logger.info(
                            "Leaving Chrome open for inspection. Press Ctrl+C to close and quit the browser."
                        )
                        try:
                            while True:
                                time.sleep(1)
                        except KeyboardInterrupt:
                            logger.info(
                                "User requested to close browser; quitting driver."
                            )
                            try:
                                driver.quit()
                            except Exception:
                                pass
                    return
            else:
                logger.debug("No parsable cookies found in provided cookie string.")
        except Exception:
            logger.exception(
                "Failed to parse and set session cookies from cookie string"
            )

    logger.debug("Final request headers: %s", headers)
    logger.debug("x-hydra-jwt present: %s", bool(auth.get("x-hydra-jwt")))

    # Prepare timestamped output filename inside data/output
    out_dir = os.path.join(os.getcwd(), "data", "output")
    os.makedirs(out_dir, exist_ok=True)

    # Use provided output as prefix if given, otherwise use 'menu'
    if args.output:
        base = os.path.splitext(os.path.basename(args.output))[0]
    else:
        base = "menu"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(out_dir, f"{base}_{timestamp}.xlsx")

    all_rows = []
    # Track number of requests to apply adaptive throttling to avoid 429s
    request_count = 0
    THROTTLE_EVERY = int(os.environ.get("GRAB_THROTTLE_EVERY", "1"))
    THROTTLE_MIN = int(os.environ.get("GRAB_THROTTLE_MIN_SECONDS", "1"))
    THROTTLE_MAX = int(os.environ.get("GRAB_THROTTLE_MAX_SECONDS", "5"))

    # If merchant_ids provided via CLI, use them. Otherwise fetch SIDs from Monday board/group.
    if merchant_ids:
        mids_to_fetch = merchant_ids
    else:
        BOARD_ID = 5025182611
        GROUP_ID = "group_mkys1dmf"
        col_ids = [
            "text_mky9b8z9",
            "text_mky974s9",
            "text_mky9pxvr",
            "text_mky9z4ts",
            "color_mkyfabkn",
        ]

        logger.info(
            f"Fetching Gr SIDs from Monday board {BOARD_ID}, group {GROUP_ID}..."
        )
        items = monday_utils.get_all_items_from_group(BOARD_ID, GROUP_ID, col_ids)

        mids_to_fetch = []
        seen = set()
        # map of merchant SID -> monday color column value
        merchant_meta_map = {}
        mapping = {
            "Foodnesia": "text_mky9b8z9",
            "WonderFood": "text_mky974s9",
            "Lokarasa": "text_mky9pxvr",
            "DoEat": "text_mky9z4ts",
        }

        for item in items:
            for brand, col in mapping.items():
                val = monday_utils.get_col_value(item, col).strip()
                if not val:
                    continue
                # handle multiple SIDs separated by commas or whitespace
                for part in [
                    p.strip() for p in val.replace(";", ",").split(",") if p.strip()
                ]:
                    if part not in seen:
                        seen.add(part)
                        mids_to_fetch.append(part)
                        # capture color column value for this merchant if present
                        try:
                            color_val = monday_utils.get_col_value(
                                item, "color_mkyfabkn"
                            ).strip()
                        except Exception:
                            color_val = ""
                        if color_val:
                            merchant_meta_map[part] = color_val

    for idx, mid in enumerate(mids_to_fetch):
        if driver and idx % 20 == 0 and idx != 0:
            cookies, token = extract_cookies_and_token(
                driver, required_cookies=REQUIRED_CONSUMER_COOKIES
            )
            if cookies:
                auth["cookies"] = cookies
                logger.info("Refreshed cookies from browser.")
            else:
                logger.warning(
                    "No cookies found in the browser session during refresh."
                )
            if token:
                auth["x-hydra-jwt"] = token
                logger.info("Refreshed hydra_device_token and mapped to x-hydra-jwt.")
            else:
                logger.warning(
                    "No hydra_device_token found in sessionStorage during refresh."
                )
            headers = build_headers_for_api(auth)
            session.headers.update(headers)
            # Also update session cookies
            try:
                cookie_dict = cookie_string_to_dict(auth.get("cookies") or "")
                if cookie_dict:
                    session.cookies.update(cookie_dict)
                    logger.debug(
                        "Session cookies refreshed: %s", session.cookies.get_dict()
                    )
                    # Validate required cookies after refresh
                    if not ensure_required_cookies_present(
                        cookie_dict,
                        "refresh",
                        required_keys=REQUIRED_CONSUMER_COOKIES,
                    ):
                        logger.error(
                            "Aborting due to missing required cookies after refresh. Browser left open for inspection."
                        )
                        if driver:
                            logger.info(
                                "Leaving Chrome open for inspection. Press Ctrl+C to close and quit the browser."
                            )
                            try:
                                while True:
                                    time.sleep(1)
                            except KeyboardInterrupt:
                                logger.info(
                                    "User requested to close browser; quitting driver."
                                )
                                try:
                                    driver.quit()
                                except Exception:
                                    pass
                        return
            except Exception:
                logger.exception("Failed to refresh session cookies from cookie string")

        logger.info(f"Fetching merchant {mid}...")
        try:
            mj = fetch_merchant(session, mid, headers)
        except Exception as e:
            logger.warning(f"Failed to fetch {mid}: {e}")
            # small backoff on failure
            # time.sleep(random.uniform(1.0, 2.0))
            request_count += 1
            # Adaptive throttle after N requests to reduce risk of 429
            if THROTTLE_EVERY > 0 and request_count % THROTTLE_EVERY == 0:
                pause = random.uniform(THROTTLE_MIN, THROTTLE_MAX)
                logger.info(
                    "Reached %s requests — pausing %.1fs",
                    request_count,
                    pause,
                )
                time.sleep(pause)
            continue

        if mj is None:
            logger.warning(f"No data returned for merchant {mid}, skipping.")
            request_count += 1
            if THROTTLE_EVERY > 0 and request_count % THROTTLE_EVERY == 0:
                pause = random.uniform(THROTTLE_MIN, THROTTLE_MAX)
                logger.info(
                    "Reached %s requests — pausing %.1fs to reduce rate-limit risk...",
                    request_count,
                    pause,
                )
                time.sleep(pause)
            continue

        rows = parse_menu(mj, brand_mapping, merchant_meta_map)
        all_rows.extend(rows)

        # Count this successful request and apply adaptive throttle when threshold reached
        request_count += 1
        if THROTTLE_EVERY > 0 and request_count % THROTTLE_EVERY == 0:
            pause = random.uniform(THROTTLE_MIN, THROTTLE_MAX)
            logger.info(
                "Reached %s requests — pausing %.1fs to reduce rate-limit risk...",
                request_count,
                pause,
            )
            time.sleep(pause)

        # polite throttle between requests
        time.sleep(random.uniform(1, 3))
    write_excel(all_rows, output_file)
    logger.info(f"Wrote {len(all_rows)} rows to {output_file}")

    # Send to Discord
    try:
        config = get_config()
        if config.DISCORD_WEBHOOK_URL:
            send_discord_file(
                config.DISCORD_WEBHOOK_URL,
                output_file,
                content=f"GrabFood Menu Extraction Complete: {os.path.basename(output_file)}",
            )
    except Exception as e:
        logger.error(f"Failed to send file to Discord: {e}")


if __name__ == "__main__":
    main()
