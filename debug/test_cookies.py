import os
import sys
import time
import json

# --- Setup Project Path ---
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.isdir(os.path.join(PROJECT_ROOT, "common")):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shopee_scrapper.browser_session import BrowserSession
from common.logger import get_logger

log = get_logger("test_cookies")

def main():
    log.info("Starting cookie test...")
    session = BrowserSession(headless=True)
    
    try:
        log.info("Logging in...")
        if session.ensure_logged_in():
            log.info("Login successful.")
        else:
            log.error("Login failed.")
            return

        log.info("Getting cookies...")
        cookies = session.driver.get_cookies()
        
        tob_token = next((c for c in cookies if c["name"] == "shopee_tob_token"), None)
        
        if tob_token:
            log.info(f"FOUND shopee_tob_token: {tob_token['value'][:10]}...")
            log.info(f"Cookie details: {json.dumps(tob_token, indent=2)}")
        else:
            log.error("shopee_tob_token NOT FOUND.")
            log.info("Available cookies:")
            for c in cookies:
                log.info(f" - {c['name']} (Domain: {c.get('domain')})")
                
    except Exception as e:
        log.error(f"Error: {e}")
    finally:
        session.quit()

if __name__ == "__main__":
    main()
