import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from common.logger import get_logger

# Use the centralized logger
log = get_logger("shopee_utils")


def get_current_merchant_name(driver, wait: WebDriverWait):
    """Gets the name of the currently active merchant from the dashboard."""
    try:
        wait.until(EC.url_contains("https://partner.shopee.co.id/food/dashboard"))
        name_element = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//div[@class='merchantName']"))
        )
        return name_element.text
    except (TimeoutException, NoSuchElementException):
        log.warning("Could not determine the current merchant name on the dashboard.")
        return None


def switch_merchant(driver, wait: WebDriverWait, merchant_info: dict):
    """Switches to a different merchant account via the UI."""
    log.info(
        f"--- Attempting to switch to merchant: {merchant_info['validate_name']} ---"
    )
    try:
        driver.get("https://partner.shopee.co.id/food/dashboard")
        time.sleep(random.uniform(2, 4))
        actions = ActionChains(driver)
        profile_menu = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "li[data-menu-id*='account']")
            )
        )
        actions.move_to_element(profile_menu).perform()
        time.sleep(random.uniform(0.5, 1))
        switch_merchant_menu = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//span[text()='Pilih Merchant Lain']")
            )
        )
        actions.move_to_element(switch_merchant_menu).perform()
        time.sleep(random.uniform(0.5, 1))
        target_merchant_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    f"//span[contains(@class, 'sc-dhKdcB') and text()='{merchant_info['click_name']}']",
                )
            )
        )
        target_merchant_button.click()
        log.info("  Validating merchant switch...")
        wait.until(EC.url_contains("https://partner.shopee.co.id/food/dashboard"))
        wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    f"//div[@class='merchantName' and text()='{merchant_info['validate_name']}']",
                )
            )
        )
        log.info(f"✅ Successfully switched to {merchant_info['validate_name']}.")
        return True
    except (TimeoutException, NoSuchElementException) as e:
        log.error(
            f"❌ Failed to switch to merchant {merchant_info['validate_name']}. Details: {e}",
        )
        return False
