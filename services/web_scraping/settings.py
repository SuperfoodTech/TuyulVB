# This file contains non-sensitive application settings and configurations for web scraping.

# --- Grab Portal Configuration ---
GRAB_MERCHANT_CONFIG = {
    "login_url": "https://weblogin.grab.com/merchant/login?service_id=MEXUSERS&redirect=https%3A%2F%2Fmerchant.grab.com%2Fportal",
    "logout_url": "https://merchant.grab.com/profile/logout",
    "merchant_list_url": "https://merchant.grab.com/food/menu",
    "username_field_id": "Username",
    "password_field_id": "password",
    "continue_after_username_xpath": "//button[contains(@class, 'dui-btn') and .//span[text()='Continue']]",
    "continue_after_password_xpath": "//button[contains(@class, 'ant-btn') and .//span[text()='Continue']]",
    "profile_dir": "grab_profile",
}

# --- Shopee Portal Configuration ---
SHOPEE_MERCHANT_CONFIG = {
    "login_url": "https://partner.business.accounts.shopee.co.id/authenticate/login/",
    "pos_url": "https://partner.shopee.co.id/shopee-pos",
    "profile_dir": "shopee_profile",
}

# --- API endpoints ---
GRAB_TARGET_API_URL = "https://api.grab.com/delvplatformapi/merchant/v1/merchant-group/store/search"
GRAB_SINGLE_OUTLET_CHECK_URL = "https://portal.grab.com/foodtroy/v1/ID/merchant-groups/catalog-stores"
SHOPEE_API_PATTERN = r'foody\.shopee\.co\.id/api/seller/stores?$'
