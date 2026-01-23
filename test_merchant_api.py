"""
Test script to validate the GetUserInfo API endpoint and debug responses.
Run after logging in via the scheduler.
"""

import sys
import requests
import json
from datetime import datetime

sys.path.insert(0, ".")

# Constants
PARTNER_API_BASE = "https://api.partner.shopee.co.id/nb/mss/web-api"
ENDPOINTS_TO_TEST = [
    # Provided endpoint
    f"{PARTNER_API_BASE}/PartnerAccountServer/GetUserInfo",
    # Alternative patterns
    f"{PARTNER_API_BASE}/PartnerAccountServer/GetCurrentMerchant",
    f"{PARTNER_API_BASE}/PartnerServer/GetUserInfo",
    f"{PARTNER_API_BASE}/PartnerServer/GetCurrentUser",
    "https://partner.shopee.co.id/api/v1/merchant/info",
    "https://partner.shopee.co.id/api/v1/user/info",
]


def test_endpoints_with_cookies(cookies_dict):
    """Test multiple endpoints with the provided cookies."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    print("\n" + "=" * 80)
    print(f"Testing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print(f"\n🍪 Cookies available: {list(cookies_dict.keys())}")
    print(f"\n📤 Headers: {headers}\n")

    for endpoint in ENDPOINTS_TO_TEST:
        print(f"\n{'─'*80}")
        print(f"Testing: {endpoint}")
        print(f"{'─'*80}")

        try:
            response = requests.post(
                endpoint,
                cookies=cookies_dict,
                headers=headers,
                json={},
                timeout=10,
            )

            print(f"✓ Status Code: {response.status_code}")
            print(f"✓ Response Headers: {dict(response.headers)}")

            try:
                data = response.json()
                print(f"✓ Response Body (formatted):")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except:
                print(f"✓ Response Body (raw):")
                print(response.text[:500])

        except requests.exceptions.Timeout:
            print(f"✗ TIMEOUT: Request took too long")
        except requests.exceptions.HTTPError as e:
            print(f"✗ HTTP ERROR: {e.response.status_code}")
            print(f"  Response: {e.response.text[:200]}")
        except requests.exceptions.RequestException as e:
            print(f"✗ REQUEST ERROR: {e}")
        except Exception as e:
            print(f"✗ ERROR: {e}")


def test_with_sample_cookies():
    """Test with hardcoded sample cookies (for manual testing)."""
    # These would need to be filled in manually from an active session
    sample_cookies = {
        "shopee_tob_token": "your_token_here",
        "shopee_tob_entity_id": "your_entity_id_here",
    }
    test_endpoints_with_cookies(sample_cookies)


if __name__ == "__main__":
    print(
        """
╔════════════════════════════════════════════════════════════════════════════╗
║                     MERCHANT API ENDPOINT TESTER                          ║
║                                                                            ║
║ Usage:                                                                     ║
║   1. Import this module in your scheduler/browser session                 ║
║   2. Call: test_endpoints_with_cookies(cookies_from_driver)              ║
║   3. Review output to find working endpoint                              ║
╚════════════════════════════════════════════════════════════════════════════╝
    """
    )

    print("\n📋 Available endpoints to test:")
    for i, endpoint in enumerate(ENDPOINTS_TO_TEST, 1):
        print(f"  {i}. {endpoint}")

    print("\n💡 Example usage in Python:")
    print(
        """
from selenium import webdriver
from test_merchant_api import test_endpoints_with_cookies

driver = webdriver.Chrome()
driver.get("https://partner.shopee.co.id/food/dashboard")
# ... login if needed ...

cookies_dict = {cookie["name"]: cookie["value"] for cookie in driver.get_cookies()}
test_endpoints_with_cookies(cookies_dict)
    """
    )
