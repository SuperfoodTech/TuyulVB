import os
# services/config.py

# --- Google Sheets Configuration ---
GOOGLE_SHEET_NAME = 'REPLACE_WITH_GOOGLE_SHEET_NAME'
INPUT_WORKSHEET_NAME = 'REPLACE_WITH_INPUT_WORKSHEET_NAME'

# --- Grab Portal Configuration ---
GRAB_MERCHANT_CONFIG = {
    "login_url": "https://weblogin.grab.com/merchant/login?service_id=MEXUSERS&redirect=https%3A%2F%2Fmerchant.grab.com%2Fportal",
    "logout_url": "https://merchant.grab.com/profile/logout",
    "merchant_list_url": "https://merchant.grab.com/food/menu",
    "username_field_id": "Username",
    "password_field_id": "password",
    "continue_after_username_xpath": "//button[contains(@class, 'dui-btn') and .//span[text()='Continue']]",
    "continue_after_password_xpath": "//button[contains(@class, 'ant-btn') and .//span[text()='Continue']]",
}

# --- API & Spreadsheet Configuration ---
TARGET_API_URL = "https://api.grab.com/delvplatformapi/merchant/v1/merchant-group/store/search"
SINGLE_OUTLET_CHECK_URL = "https://portal.grab.com/foodtroy/v1/ID/merchant-groups/catalog-stores"

COLUMN_MAPPING = [
    {
        "source_portal": "F1",
        "outlet_name": "Nama Outlet Asli Merchant",
        "id_col": "SID Gr F",
        "ofd_name_col": "Nama Gr F"
    },
    {
        "source_portal": "F2",
        "outlet_name": "Nama Outlet Asli Merchant",
        "id_col": "SID Gr F",
        "ofd_name_col": "Nama Gr F"
    },
    {
        "source_portal": "F2S",
        "outlet_name": "Nama Outlet Asli Merchant",
        "id_col": "SID Gr F",
        "ofd_name_col": "Nama Gr F"
    },
    {
        "source_portal": "W1",
        "outlet_name": "Nama Outlet Asli Merchant",
        "id_col": "SID Gr W",
        "ofd_name_col": "Nama Gr W"
    },
    {
        "source_portal": "L1",
        "outlet_name": "Nama Outlet Asli Merchant",
        "id_col": "SID Gr L",
        "ofd_name_col": "Nama Gr L"
    },
    {
        "source_portal": "L2",
        "outlet_name": "Nama Outlet Asli Merchant",
        "id_col": "SID Gr L",
        "ofd_name_col": "Nama Gr L"
    },
    {
        "source_portal": "DE1S",
        "outlet_name": "Nama Outlet Asli Merchant",
        "id_col": "SID Gr DE",
        "ofd_name_col": "Nama Gr DE"
    }
]

OUTPUT_WORKSHEET_NAME = COLUMN_MAPPING[0]["source_portal"]

# --- Shopee Portal Configuration ---
SHOPEE_PARTNER_CONFIG = {
    "login_url": "https://partner.business.accounts.shopee.co.id/authenticate/login/",
    "logout_url": "https://partner.shopee.co.id/logout",
    "merchant_list_url": "https://partner.shopee.co.id/shopee-pos",
    "username_field_id": "Username",
    "password_field_id": "password",
}

# --- Monday.com API Configuration ---
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_BOARD_ID = 2075992045  # Board ID for main operations

# --- Monday.com Duplication Watcher Configuration ---
MONDAY_DUPLICATION_BOARD_ID = 2075483964  # Board ID for duplication checking
MONDAY_TARGET_GROUP_ID = "group_mkvxp4cr"
MONDAY_TARGET_GROUP_NAME = "Merchant - Outlet - VB (Database)"
DUPLICATE_CHECKS = [
    {'source': 'Name', 'target': 'Name Dup'},
    {'source': 'SID Gr F', 'target': 'SID Gr F Dup'},
    {'source': 'SID Gr W', 'target': 'SID Gr W Dup'},
    {'source': 'SID Gr L', 'target': 'SID Gr L Dup'},
    {'source': 'SID Gr DE', 'target': 'SID Gr DE Dup'},
    {'source': 'SID S F', 'target': 'SID S F Dup'},
    {'source': 'SID S W', 'target': 'SID S W Dup'},
    {'source': 'SID S L', 'target': 'SID S L Dup'},
]
