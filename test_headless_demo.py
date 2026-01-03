"""
Test script to demonstrate headless vs headed Chrome automation
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def test_headless_vs_headed():
    """Test both headless and headed modes"""

    print("Testing Chrome automation modes...")
    print("=" * 50)

    # Test Headed Mode (visible browser)
    print("\n1. Testing HEADED mode (visible browser window):")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    driver.get("https://www.google.com")
    time.sleep(2)

    title = driver.title
    print(f"   Page title: {title}")
    print("   ✅ You should see a visible Chrome window")

    driver.quit()
    print("   Browser closed")

    # Test Headless Mode (invisible)
    print("\n2. Testing HEADLESS mode (invisible, background):")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    driver.get("https://www.google.com")
    time.sleep(2)

    title = driver.title
    print(f"   Page title: {title}")
    print("   ✅ No visible browser window - runs in background")

    driver.quit()
    print("   Browser closed")

    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("• Headless mode: Chrome runs invisibly, perfect for servers")
    print("• Headed mode: Chrome shows visible window, good for debugging")
    print("• Clicking works in BOTH modes - headless just hides the UI")
    print("• Use headless for production, headed for development/debugging")


if __name__ == "__main__":
    test_headless_vs_headed()
