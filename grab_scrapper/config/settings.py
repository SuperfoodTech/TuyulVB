# settings.py for grab_scrapper

# --- Debugging and Output Configuration ---
# Set to True to save the raw, uncleaned data from scrapers into a JSON file for debugging.
# Set to False for normal production runs to save disk space.
SAVE_RAW_DATA_FOR_DEBUG = True

# --- Monday.com Configuration ---
# Board ID for the main merchant database where data will be uploaded.
MONDAY_BOARD_ID = 5004455392

# Group mappings for different source portals on the Monday.com board.
# The 'source_portal' should match the account name in `credentials.py`.
MONDAY_TARGET_GROUP = [
    {"source_portal": "F1", "group_id": "group_mkw46q72", "group_name": "F1"},
    {"source_portal": "F2", "group_id": "group_mkw4bpf5", "group_name": "F2"},
    {"source_portal": "F2S", "group_id": "group_mks9kmgx", "group_name": "Temp"},
    {"source_portal": "W1", "group_id": "group_mks93rx3", "group_name": "W1"},
    {
        "source_portal": "L1",
        "group_id": "group_mkw4rjmz",
        "group_name": "Lokarasa (L1)",
    },
    {"source_portal": "L2", "group_id": "group_mks9ghrx", "group_name": "L2"},
    {"source_portal": "DE1", "group_id": "group_mkw45f1v", "group_name": "DE1"},
    {"source_portal": "DE1S", "group_id": "group_mks9qqwm", "group_name": "DE1S"},
    {"source_portal": "S1", "group_id": "group_mkw4487b", "group_name": "S1"},
    {"source_portal": "H1", "group_id": "group_mkw41eee", "group_name": "H1"},
    {"source_portal": "K1", "group_id": "group_mkw4491t", "group_name": "K1"},
    {"source_portal": "E1", "group_id": "group_mkw49hry", "group_name": "E1"},
    {"source_portal": "R1", "group_id": "group_mkw42h0d", "group_name": "R1"},
    {"source_portal": "D1", "group_id": "group_mkw4bad7", "group_name": "D1"},
    {"source_portal": "T1", "group_id": "group_mkw4fjah", "group_name": "T1"},
    {"source_portal": "FM1", "group_id": "group_mkw4cg1g", "group_name": "FM1"},
    {"source_portal": "FM2", "group_id": "group_mkw4g5x1", "group_name": "FM2"},
    {"source_portal": "FM3", "group_id": "group_mkw4bat0", "group_name": "FM3"},
    {"source_portal": "FM4", "group_id": "group_mkw4nw23", "group_name": "FM4"},
]

# --- Grab Portal & API Configuration ---
GRAB_MERCHANT_CONFIG = {
    "login_url": "https://weblogin.grab.com/merchant/login?service_id=MEXUSERS&redirect=https%3A%2F%2Fmerchant.grab.com%2Fportal",
    "logout_url": "https://merchant.grab.com/profile/logout",
    "merchant_list_url": "https://merchant.grab.com/food/menu",
    "username_field_id": "Username",
    "password_field_id": "password",
    "continue_after_username_xpath": "//button[contains(@class, 'dui-btn') and .//span[text()='Continue']]",
    "continue_after_password_xpath": "//button[contains(@class, 'dui-btn') and .//span[text()='Continue']]",
}

# API endpoint for multi-outlet accounts
TARGET_API_URL = (
    "https://api.grab.com/delvplatformapi/merchant/v1/merchant-group/store/search"
)
# API endpoint for single-outlet accounts
SINGLE_OUTLET_CHECK_URL = (
    "https://portal.grab.com/foodtroy/v1/ID/merchant-groups/catalog-stores"
)
