"""
REFACTORED extract_raw.py - API-Based Extraction
Eliminates Selenium pagination for 100x faster performance.
"""

import json
import time
import os
import re
import requests
import random
from datetime import datetime
from common.logger import get_logger

try:
    from modules.shopee.browser_session import BrowserSession
    from common.shopee_utils import get_current_merchant_name, switch_merchant
    from config.credentials_shopee import ACCOUNT_CREDS
    from config.settings_shopee import MERCHANT_PROCESSING_LIST
    from modules.shopee.api_utils import extract_auth_tokens, get_shopee_headers
except ImportError as e:
    print(f"[FATAL] Import error: {e}")
    exit()

log = get_logger("extract_store_raw")
log.propagate = False

# API Configuration
SHOPEE_API_BASE = "https://foody.shopee.co.id"
API_TIMEOUT = 10


def collect_shopee_raw_data(browser_session, merchant_name):
    """
    Collects store data using direct API calls and saves it to a JSON file.
    """
    driver = browser_session.driver
    safe_merchant_name = re.sub(r'[\\/*?:\"<>|]', "", merchant_name).replace(" ", "_")
    
    # 1. Ensure Login
    if not browser_session.ensure_logged_in():
        log.critical("  Failed to ensure login. Aborting.")
        return None

    # 2. Extract Tokens
    tob_token, entity_id = extract_auth_tokens(driver)
    if not tob_token:
        return None
        
    if not entity_id:
        log.warning("  shopee_tob_entity_id not found. Using empty string (API might reject).")
        entity_id = ""

    # 3. Fetch Data via API
    headers = get_shopee_headers(tob_token, entity_id)
    all_stores = []
    page = 1
    page_size = 50
    
    log.info(f"  Starting API extraction for {merchant_name}...")
    
    while True:
        log.info(f"  Fetching Page {page} (Size: {page_size})...")
        
        payload = {
            "filter": {},
            "page_no": page,
            "page_size": page_size
        }
        
        try:
            url = f"{SHOPEE_API_BASE}/api/seller/stores/search"
            response = requests.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                log.error(f"  Failed to parse API response: {response.text[:100]}...")
                break
                
            if data.get("code") != 0:
                if data.get("code") == 100002 and data.get("msg") == "mis svr err":
                    log.warning("  Encountered 'mis svr err' (Code 100002). Waiting 5 minutes before retrying...")
                    time.sleep(300)
                    continue

                log.error(f"  API Error: {data.get('msg')}")
                break
            
            store_list = data.get("data", {}).get("store_basic_info_list", [])
            
            if not store_list:
                log.info("  No more stores returned by API. Extraction complete.")
                break
                
            all_stores.extend(store_list)
            log.info(f"  + {len(store_list)} stores. Total: {len(all_stores)}")
            
            # Check if we've reached the end based on page size
            if len(store_list) < page_size:
                log.info("  Partial page received. Reached end of list.")
                break
                
            page += 1
            time.sleep(random.uniform(0.5, 1.0)) # Polite delay
            
        except requests.exceptions.RequestException as e:
            log.error(f"  Network error during API call: {e}")
            break
        except Exception as e:
            log.error(f"  Unexpected error: {e}")
            break

    # 4. Save Data
    if all_stores:
        raw_output_dir = "raw_data"
        os.makedirs(raw_output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"shopeefood_{safe_merchant_name}_{timestamp}.json"
        filepath = os.path.join(raw_output_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(all_stores, f, indent=2, ensure_ascii=False)
            log.info(f"✅ Saved {len(all_stores)} stores to '{filepath}'.")
            return filepath
        except Exception as e:
            log.error(f"  Failed to save file: {e}")
            return None
    else:
        log.warning("  No data collected.")
        return None


def run_raw_extraction(browser_session, merchant_task):
    """
    Entry point for raw data extraction.
    """
    collect_shopee_raw_data(browser_session, merchant_task["output_name"])