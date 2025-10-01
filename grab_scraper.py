from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re


class GrabScraper:
    def __init__(self, driver_path):
        self.driver = webdriver.Chrome(executable_path=driver_path)
        self.wait = WebDriverWait(self.driver, 10)

    def search_restaurant(self, restaurant_name, location):
        self.driver.get("https://food.grab.com/ph/en/")

        location_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "location-input")))
        location_input.send_keys(location)
        time.sleep(1)
        location_input.send_keys(Keys.ENTER)

        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, f"//h3[text()='{location}']")))
        self.driver.find_element(
            By.XPATH, f"//h3[text()='{location}']").click()

        search_button = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Search')]")))
        search_button.click()

        search_input_restaurant = self.wait.until(
            EC.presence_of_element_located((By.ID, "search-input")))
        search_input_restaurant.send_keys(restaurant_name)
        search_input_restaurant.send_keys(Keys.ENTER)

        try:
            restaurant_element = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, f"//p[contains(text(), '{restaurant_name}')]")))
            restaurant_element.click()
            return self.driver.current_url
        except:
            return "Not Found"

    def close(self):
        self.driver.quit()
