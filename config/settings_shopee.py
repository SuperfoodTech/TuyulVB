# settings.py
import os

# --- Debugging and Output Configuration ---
# Set to True to save the raw, uncleaned data from scrapers into a JSON file for debugging.
# Set to False for normal production runs to save disk space.
SAVE_RAW_DATA_FOR_DEBUG = True

# --- Data Provider & Database Configuration ---
# Options for DATA_PROVIDER_TYPE: 'hybrid', 'sheets', 'vercel', 'database', 'local_json'
DATA_PROVIDER_TYPE = "hybrid"
GOOGLE_SHEET_ID = "10osh4rI4q_mv6fBe9NurXRztRrGa85L01Bwned6m0Qs"
VERCEL_API_URL = ""
VERCEL_API_TOKEN = ""

# Database Backup Settings
DATABASE_PATH = "data/db/tuyul_vb.db"
ENABLE_DATABASE_BACKUP = True

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
    {"click_name": "LOKARASA", "validate_name": "LOKARASA", "output_name": "Lokarasa"},
    {
        "click_name": "Gurame Bakar, Do Eat",
        "validate_name": "Gurame Bakar, Do Eat",
        "output_name": "DoEat",
    },
]

# Monday Board & Group Mapping
MONDAY_BOARD_ID = os.environ.get("MONDAY_BOARD_ID", "1234567890")
GROUP_MAPPING = {
    "Foodnesia": "group_foodnesia",
    "WonderFood": "group_wonderfood",
    "Lokarasa": "group_lokarasa",
    "DoEat": "group_doeat",
}

# --- API Configuration ---
COOKIE_CACHE_TTL = 3600
API_MAX_CONCURRENT_REQUESTS = 5
API_REQUEST_TIMEOUT = {"connection": 10, "read": 30, "total": 60}
API_RETRY_ATTEMPTS = 3
API_BASE_RETRY_DELAY = 1.0
DRY_RUN = False
