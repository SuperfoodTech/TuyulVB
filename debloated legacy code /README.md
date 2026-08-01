# Superfood Automation Suite

A comprehensive Python automation platform for scraping merchant data from Shopee and Grab portals, performing address validation against Klikit, and synchronizing all data to Monday.com. The suite provides a centralized command-line interface for managing complex workflows across multiple platforms.

## Overview

This repository contains:
- **Data Scraping**: Extract store details, short names, customer data, and merchant information from Shopee and Grab portals
- **Address Validation**: Validate and sync addresses against Klikit database with automated reconciliation
- **Data Synchronization**: Automated syncing to Monday.com boards with duplicate detection
- **Monitoring & Watches**: Long-running processes that continuously monitor Monday.com boards for data quality issues
- **Batch Operations**: Support for dry-run modes and bulk updates across multiple merchants

## Key Features

- **Centralized CLI Interface**: Menu-driven `run.py` for executing all scripts with a consistent experience
- **Configuration Health Check**: Built-in validation to verify all configs, credentials, and dependencies
- **Persistent Browser Sessions**: Selenium profiles maintain login sessions across multiple runs
- **Advanced Scraping**: Hybrid UI interaction and API interception for reliable data extraction
- **Klikit Integration**: Automated address validation and synchronization with Klikit database
- **Dry-Run Support**: Test any sync operation before committing changes
- **Unified Sync**: Combined Shopee/Grab data sync to reduce redundant operations
- **Comprehensive Logging**: Detailed logs with configurable output for debugging and auditing

## Prerequisites

- **Python 3.8+**
- **Google Chrome** browser installed
- Accounts and API access to:
  - Shopee Partner Portal
  - Grab Merchant Portal
  - Monday.com (API key required)
  - Klikit database (for address validation)

## 📋 Installation & Setup

### 1. Automated Installation (Linux / Raspberry Pi)

Run the one-command installer:

```bash
./setup.sh
```

### 2. Manual Installation

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root directory:

```ini
MONDAY_API_KEY="your_monday_api_v2_key_here"
DISCORD_WEBHOOK_URL="your_discord_webhook_url_here"  # Optional
```

Copy from `.env.example` as a template if available.

### 3. Configure Shopee Scraper

**File: `shopee_scrapper/config/credentials.py`**

```python
ACCOUNT_CREDS = {
    "shopee_master_account": {
        "username": "your_shopee_username",
        "password": "your_shopee_password"
    }
}
```

**File: `shopee_scrapper/config/settings.py`**

```python
MERCHANT_PROCESSING_LIST = [
    {"validate_name": "Portal Merchant Name 1", "output_name": "Desired Output Name 1"},
    {"validate_name": "Portal Merchant Name 2", "output_name": "Desired Output Name 2"},
]

MONDAY_BOARD_ID = 1234567890

GROUP_MAPPING = {
    "Desired Output Name 1": "group_id_for_merchant_1",
    "Desired Output Name 2": "group_id_for_merchant_2",
}
```

**File: `shopee_scrapper/config/addressettings.py`** (for address validation)

Configure settings for address validation against Klikit.

### 4. Configure Grab Scraper

**File: `grab_scrapper/config/credentials.py`**

```python
ACCOUNT_CREDS = {
    "GRAB_ACCOUNT_1": {
        "username": "your_grab_username_1",
        "password": "your_grab_password_1"
    },
    "GRAB_ACCOUNT_2": {
        "username": "your_grab_username_2",
        "password": "your_grab_password_2"
    }
}
```

**File: `grab_scrapper/config/settings.py`**

```python
GRAB_MERCHANT_CONFIG = {
    "login_url": "https://merchant.grab.com/portal/login",
    "logout_url": "https://merchant.grab.com/portal/logout",
    "merchant_list_url": "https://merchant.grab.com/portal/menu",
    "username_field_id": "username",
    "password_field_id": "password",
    "continue_after_username_xpath": "//button[@type='submit']",
    "continue_after_password_xpath": "//button[@type='submit']",
}

TARGET_API_URL = "merchant.grab.com/merchant-hq-api/merchants"
SINGLE_OUTLET_CHECK_URL = "merchant.grab.com/merchant-hq-api/merchant"

MONDAY_BOARD_ID = 1234567890

MONDAY_TARGET_GROUP = [
    {"source_portal": "GRAB_ACCOUNT_1", "group_id": "group_id_for_account_1"},
    {"source_portal": "GRAB_ACCOUNT_2", "group_id": "group_id_for_account_2"},
]
```

### 5. Configure Monday.com Integration

**File: `monday_automation/config/dupsettings.py`**

Configure board IDs, group IDs, and column mappings for duplicate detection and data syncing.

### 6. Run Health Check

After configuration, verify everything is set up correctly:

```bash
python run.py
```

Select "Run Health Check" from the menu. This validates:
- All required config files exist and are readable
- Environment variables are configured
- Python dependencies are installed
- API keys are accessible

## 🚀 Usage

### Main Runner

```bash
python run.py
```

This presents an interactive menu with all available scripts organized by platform.

### First-Time Setup

For scripts requiring Shopee login:

1. Run the desired Shopee script (e.g., "Shopee: Extract Raw Store Data")
2. Select "Manual Login Setup" from the sub-menu
3. Complete login manually in the browser window (handle any CAPTCHAs)
4. Close the browser; session is saved to `selenium_profiles/shopee_profile`
5. Script can now run automatically on future executions

## 📚 Available Scripts

### Shopee Portal Scraping

1. **Shopee: Extract Raw Store Data**
   - Extracts raw merchant data from Shopee Partner portal
   - Stores output in structured format for further processing

2. **Shopee: Get Full Store Details**
   - Scrapes comprehensive store information (status, address, contact details)
   - Syncs directly to Monday.com board

3. **Shopee: Get Store Short Names**
   - Extracts merchant short names from Shopee portal
   - Updates Monday.com "Short Name" column

4. **Shopee: Get Customer Details from Transactions**
   - Scrapes transaction data including customer names and phone numbers
   - Exports to Excel file in `scraped_data` directory

### Grab Portal Integration

5. **Grab: Get Merchant Data**
   - Intercepts API calls to extract merchant data from Grab Merchant portal
   - Uploads to Monday.com board

6. **Grab: Address Validation**
   - Validates outlet addresses from Monday.com against live Grab portal data
   - Generates detailed validation report

### Klikit Address Validation & Sync

7. **Shopee: Address Validation**
   - Validates Shopee merchant addresses against Klikit database

8. **Shopee: Klikit Address Validation**
   - Comprehensive validation against Klikit with sync capability

9. **Shopee: Klikit Address Validation - DRY RUN**
   - Preview validation results without making any changes

10. **Shopee: Klikit OPH Sync (Open/Closed)**
    - Syncs Open/Closed status from Shopee to Klikit

11. **Shopee/Grab: Unified Klikit Sync (Address & OPH)**
    - Combined sync for both address and OPH status from both Shopee and Grab
    - Reduces redundant operations and consolidates data flow

12. **Grab: Klikit Address Validation**
    - Validates Grab merchant addresses against Klikit database

### Monday.com Monitoring & Synchronization

13. **Monday: Watch for Duplicates Board SSOT**
    - Continuous monitoring of SSOT (Single Source of Truth) board
    - Detects and flags duplicate values in specified columns
    - Runs as background process

14. **Monday: Watch for Duplicates Board VBO Naming**
    - Monitors VBO (VirtualBand Outlet) board for naming duplicates
    - Updates status column with findings
    - Long-running background process

15. **Monday: Watch for Duplicates Board Manual Disbursement (Order ID)**
    - Monitors Manual Disbursement board for duplicate Order IDs
    - Continuous background monitoring

16. **Monday: Input WA Numbers from Excel**
    - Reads WhatsApp numbers from Excel source file
    - Matches outlet names with WA numbers
    - Updates "WA Number" column on target Monday.com board

17. **Monday: Sync Short Names (Pull → SSOT)**
    - Pulls Store ID and Short Name from source board
    - Syncs Short Name to target SSOT board based on Store ID match

### Data Synchronization (Full Workflows)

18. **Monday: Sync Full & Short Names (VB Database)**
    - Combined sync of full store details and short names to VB Database board
    - Updates all merchant information in single operation

19. **Monday: Sync Full & Short Names (VB Database) - DRY RUN**
    - Preview mode for VB Database sync without making changes

20. **Monday: Sync Full & Short Names (Klikit Migration Database)**
    - Syncs to Klikit Migration Database board
    - Handles migration-specific field mappings

21. **Monday: Sync Full & Short Names (Klikit Migration Database) - DRY RUN**
    - Preview mode for Klikit Migration Database sync

### Store Status Automation

22. **Shopee: Force Open/Close Scheduler**
    - **Script**: `shopee_scrapper/force_open_scheduler.py` (or `run_force_open_scheduler.bat`)
    - **Function**: Continuously monitors Monday.com for store status override requests (runs every 15 minutes).
    - **Logic**:
      - **Input**: Checks Monday.com column for "Yes X" (where X <= Scale Level) and "Closed Req" status.
      - **Open Action**: If "Closed Req" is empty/Open, ensures store is "Buka". If currently "Tutup Sementara", it clicks "Buka Outlet".
      - **Close Action**: If "Closed Req" is "Closed", ensures store is "Tutup Sementara". If currently "Buka", it clicks "Tutup Outlet Sementara" -> "Sepanjang Hari".
      - **Validation**: Double-checks success via network API response (primary) and UI badge status (secondary).
    - **Reporting**: Sends consolidated Discord notifications with stacked fields (Forced Open, Forced Close, Already Open, Failed, etc.).

## 🔧 Advanced Features

### Dry-Run Mode

Several scripts support `--dry-run` flag to preview changes:

```bash
python monday_automation/sync-shopee-grab-vbo.py --dry-run
```

This displays what would be changed without committing updates.

### Manual Profile Reset

To clear a corrupted browser session:

1. Run the relevant Shopee script
2. Select "Reset Profile (Clear Session)" from sub-menu
3. Confirm deletion
4. Next run will require fresh login

### Configuration Files

State and configuration are maintained in JSON files:

- `monday_state_ssot.json` - State for SSOT board monitoring
- `monday_state_vbo.json` - State for VBO board monitoring
- `monday_state_orderid.json` - State for Order ID board monitoring

These files track duplicates and changes across script runs.

## 📂 Directory Structure

```
sf-automation/
├── common/                    # Shared utilities
│   ├── logger.py
│   ├── monday_api.py          # Monday.com API wrapper
│   ├── notifications.py       # Discord/notification integration
│   └── shopee_utils.py
├── shopee_scrapper/          # Shopee portal scraping
│   ├── main_runner.py
│   ├── sync_store_details.py
│   ├── sync_short_names.py
│   ├── sync_address_klikit.py
│   ├── sync_klikit_unified.py
│   ├── shopee_customer.py
│   └── config/
├── grab_scrapper/            # Grab portal scraping
│   ├── monday-grab-extract.py
│   ├── monday-grab-address-validation.py
│   ├── sync_address_klikit_grab.py
│   └── config/
├── monday_automation/        # Monday.com sync & monitoring
│   ├── watch_duplicates_ssot.py
│   ├── watch_duplicates_vbo.py
│   ├── watch_duplicates_orderid.py
│   ├── short_name_updater.py
│   ├── input-wa.py
│   ├── sync-shopee-grab-vbo.py
│   ├── sync-shopee-grab-klikit.py
│   └── config/
├── monday_checker/           # Monday.com connection & debugging
├── selenium_profiles/        # Persistent browser sessions
├── run.py                    # Main entry point
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (not in repo)
└── README.md
```

## 🛠️ Dependencies

Key Python packages:
- `selenium` & `selenium-wire` - Browser automation and API interception
- `requests` - HTTP requests to Monday.com and other APIs
- `pandas` - Data manipulation and Excel I/O
- `openpyxl` - Excel file operations
- `python-dotenv` - Environment variable management
- `webdriver-manager` - Automated Chrome driver management
- `tqdm` - Progress bars for long-running operations

## 📝 Logging & Debugging

All scripts output detailed logs to console with timestamps. For detailed debugging:

1. Check console output for error messages and stack traces
2. Review JSON state files for tracking information
3. Use dry-run mode to preview changes before execution
4. Check `debug.log` if generated

## ⚠️ Important Notes

- Some scripts are long-running background processes (watch_duplicates_*). Stop them with Ctrl+C
- Address validation requires Klikit database access credentials
- Monday.com API has rate limits; scripts include retry logic with exponential backoff
- Browser sessions persist across runs; reset profiles if experiencing login issues
- Dry-run modes are recommended for testing before deploying sync operations

## 🐛 Troubleshooting

### "Config file not found" errors
- Verify all required config files exist in the respective `config/` directories
- Check file permissions are readable

### Monday.com API errors
- Confirm `MONDAY_API_KEY` is correct in `.env` file
- Verify board IDs and column IDs are correct in configuration
- Check API rate limits haven't been exceeded

### Browser session failures
- Clear the session: Select "Reset Profile (Clear Session)"
- Ensure Chrome browser is installed and up to date
- Check internet connection for portal access

### Address validation failures
- Verify Klikit database connection and credentials
- Confirm merchant names/IDs match between portals
- Review validation report for specific mismatches
