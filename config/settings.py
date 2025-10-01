import os
from pathlib import Path
from dotenv import load_dotenv


def load_config():
    """Load configuration from .env file"""
    base_dir = Path(__file__).parent.parent
    env_path = base_dir / 'config' / '.env'
    load_dotenv(dotenv_path=env_path)

    return {
        'credentials_path': base_dir / os.getenv('CREDENTIALS_PATH'),
        'spreadsheet_id': os.getenv('SPREADSHEET_ID'),
        'worksheet_name': os.getenv('WORKSHEET_NAME'),
        'driver_path': base_dir / os.getenv('DRIVER_PATH'),
        'delay_between_requests': float(os.getenv('DELAY_BETWEEN_REQUESTS', '2.0')),
        'max_retries': int(os.getenv('MAX_RETRIES', '3'))
    }


# --- Grab Merchant Portal Configuration ---
GRAB_MERCHANT_CONFIG = {
    "login_url": "https://merchant.grab.com/portal/login",
    "logout_url": "https://merchant.grab.com/portal/logout",
    "merchant_list_url": "https://merchant.grab.com/portal/menu",
    "username_field_id": "username",
    "password_field_id": "password",
    "continue_after_username_xpath": "//button[@type='submit']",
    "continue_after_password_xpath": "//button[@type='submit']",
}

# --- Grab API Endpoint Targets ---
TARGET_API_URL = "https://merchant.grab.com/api/v1/merchants/outlets"
SINGLE_OUTLET_CHECK_URL = "https://merchant.grab.com/api/v1/merchants"

# --- Monday.com Configuration ---
MONDAY_BOARD_ID = "REPLACE_WITH_MONDAY_BOARD_ID"

# Map the source portal (from credentials.py) to the target group on your Monday.com board.
MONDAY_TARGET_GROUP = [
    {
        "source_portal": "REPLACE_WITH_ACCOUNT_1_NAME",
        "group_id": "REPLACE_WITH_MONDAY_GROUP_ID_1"
    },
    {
        "source_portal": "REPLACE_WITH_ACCOUNT_2_NAME",
        "group_id": "REPLACE_WITH_MONDAY_GROUP_ID_2"
    },
]
]
