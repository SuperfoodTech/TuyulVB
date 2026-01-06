"""
Pagination utilities for Shopee scraping.
Consolidates pagination logic used across multiple scripts.
"""

import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from common.logger import get_logger

log = get_logger("pagination_utils")


def jump_to_page(driver, wait, target_page):
    """
    Jumps to a specific page using direct input or pagination buttons.

    Tries multiple strategies:
    1. Direct input field (most efficient)
    2. Click 'Next 5 Pages' or target page directly (fallback)

    Args:
        driver: Selenium WebDriver instance
        wait: WebDriverWait instance
        target_page: Page number to jump to (integer)

    Returns:
        True if jump was successful, False otherwise
    """
    log.info(f"Attempting to jump to page {target_page}...")

    # Strategy 1: Use the direct input field (most efficient)
    log.info("  -> Trying direct input method...")
    try:
        page_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[@aria-label='Page']"),
            )
        )
        page_input.click()
        page_input.clear()
        page_input.send_keys(str(target_page))

        lanjut_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Lanjut']]"))
        )
        lanjut_button.click()
        time.sleep(random.uniform(1, 2))
        
        log.info(f"  -> Successfully jumped to page {target_page} via input.")
        return True
    except TimeoutException:
        log.warning("  -> Direct input field not found. Trying other methods...")

    log.info("  -> Trying 'Next 5 Pages' or direct page click method...")
    for attempt in range(10):  # Limit attempts to prevent infinite loops
        try:
            target_button = driver.find_element(
                By.XPATH, f"//li[@title='{target_page}']"
            )
            target_button.click()
            time.sleep(random.uniform(1, 2))
            log.info(f"  -> Successfully clicked button for page {target_page}.")
            return True
        except NoSuchElementException:
            log.info(f"  -> Page {target_page} not visible, trying 'Next 5 Pages'...")
            try:
                next_5_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//li[@title='Next 5 Pages']")
                    )
                )
                next_5_button.click()
                time.sleep(random.uniform(1.5, 2.5))
            except (NoSuchElementException, TimeoutException):
                log.warning("  -> Could not find 'Next 5 Pages' button.")
                if attempt == 9:
                    log.error(
                        "  -> Advanced jump methods failed. The main loop will now rely on clicking 'Next Page'."
                    )
                    return False
                continue

    log.critical(f"All methods to jump to page {target_page} failed.")
    return False
