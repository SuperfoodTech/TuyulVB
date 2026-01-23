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

# ============================================================================
# MERCHANT PROCESSING / MONDAY MAPPING CONFIGURATION
# ============================================================================
# Configuration for which merchants are processed and how they map to Monday
#
# Purpose:
#   - `MERCHANT_PROCESSING_LIST`: Defines the merchant profiles the runner will
#     iterate over when performing Shopee tasks.
#   - `GROUP_MAPPING`: Maps `output_name` values from the processing list to the
#     corresponding Monday.com group IDs where results will be written.
#   - `MONDAY_BOARD_ID`: The target Monday.com board where groups are located.
#
# Environment Variables (optional support patterns):
#   - SHOPEE_MERCHANTS_JSON: Path to an alternate merchant list JSON (if implemented)
#     How used: Tooling may load merchants from a file instead of hardcoding.
#     Purpose: Allow dynamic merchant lists in CI or different environments.
#   - MONDAY_BOARD_ID: If set as an env var, it should override the hardcoded board ID.
#     Purpose: Deploy to different Monday boards without changing the code.
#
# Used By: `modules/shopee/main_runner.py` and task modules invoked by it
#   - The runner reads `MERCHANT_PROCESSING_LIST` to display the menu and
#     determine which merchants to run tasks for.
#   - `GROUP_MAPPING` is used when writing results to Monday to select the
#     correct group on the board identified by `MONDAY_BOARD_ID`.
# ============================================================================

# The list of merchants to process under the master account.
MERCHANT_PROCESSING_LIST = [
    {
        "click_name": "SuperFood",
        "validate_name": "SuperFood",
        "output_name": "Foodnesia",
    },
    {
        "click_name": "WonderFood",
        "validate_name": "WonderFood",
        "output_name": "WonderFood",
    },
    # {
    #     "click_name": "Gurame Bakar, Do Eat",
    #     "validate_name": "Gurame Bakar, Do Eat",
    #     "output_name": "DoEat",
    # },
    {"click_name": "LOKARASA", "validate_name": "LOKARASA", "output_name": "Lokarasa"},
]

# --- API Configuration ---
COOKIE_CACHE_TTL = 3600
API_MAX_CONCURRENT_REQUESTS = 5
API_REQUEST_TIMEOUT = {"connection": 10, "read": 30, "total": 60}
API_RETRY_ATTEMPTS = 3
API_BASE_RETRY_DELAY = 1.0
DRY_RUN = False
