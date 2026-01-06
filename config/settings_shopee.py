# settings.py

# --- Debugging and Output Configuration ---
# Set to True to save the raw, uncleaned data from scrapers into a JSON file for debugging.
# Set to False for normal production runs to save disk space.
SAVE_RAW_DATA_FOR_DEBUG = True

# --- Monday.com Configuration ---
MONDAY_BOARD_ID = 5006292952

# Maps the 'output_name' from MERCHANT_PROCESSING_LIST to a specific Group ID on your Monday board.
GROUP_MAPPING = {
    "Foodnesia": "group_mkw46q72",
    "DoEat": "group_mkw45f1v",
    "WonderFood": "group_mks93rx3",
    "Lokarasa": "group_mkw4rjmz",
    "S1": "group_mkw4487b",
    "H1": "group_mkw41eee",
    "K1": "group_mkw4491t",
    "E1": "group_mkw49hry",
    "R1": "group_mkw42h0d",
    "D1": "group_mkw4bad7",
    "T1": "group_mkw4fjah",
    "FM1": "group_mkw4cg1g",
}

# The list of merchants to process under the master account.
MERCHANT_PROCESSING_LIST = [
    {
        "click_name": "SuperFood",
        "validate_name": "SuperFood",
        "output_name": "Foodnesia",
    },
    # {
    #     "click_name": "Gurame Bakar, Do Eat",
    #     "validate_name": "Gurame Bakar, Do Eat",
    #     "output_name": "DoEat",
    # },
    {
        "click_name": "WonderFood",
        "validate_name": "WonderFood",
        "output_name": "WonderFood",
    },
    {"click_name": "LOKARASA", "validate_name": "LOKARASA", "output_name": "Lokarasa"},
]

# --- API Configuration ---
COOKIE_CACHE_TTL = 3600
API_MAX_CONCURRENT_REQUESTS = 5
API_REQUEST_TIMEOUT = {"connection": 10, "read": 30, "total": 60}
API_RETRY_ATTEMPTS = 3
API_BASE_RETRY_DELAY = 1.0
DRY_RUN = False