# Shopee Force Open Automation

## Overview
This suite of scripts automates the process of opening or closing Shopee Food stores based on their status in a Monday.com board. It runs periodically, checks Monday.com for instructions (Open/Close), and executes them on the Shopee Partner portal via Selenium automation.

## Components

### 1. `shopee_scrapper/force_open.py`
**The Core Logic.**
- Connects to Monday.com to fetch store statuses.
- Navigates the Shopee Partner portal.
- Performs the "Open Outlet" or "Close Outlet" actions.
- Sends Discord notifications with the results.

### 2. `shopee_scrapper/force_open_scheduler.py`
**The Scheduler.**
- Runs the core logic every 15 minutes (configurable).
- Manages the browser session (keeps it alive to avoid repeated logins).
- Iterates through a list of merchants (`MERCHANT_PROCESSING_LIST`).
- Handles account switching between merchants.

### 3. `run_force_open_scheduler.bat`
**The Launcher.**
- A Windows batch file to easily start the scheduler.
- Sets the working directory and runs the python script.

## How It Works

1.  **Configuration**: The scheduler is configured with a list of merchants to process.
2.  **Scheduling**: Every 15 minutes (default), the scheduler triggers a run.
3.  **Browser Session**: It initializes a headless Chrome browser and logs into the master Shopee account.
4.  **Merchant Loop**: For each merchant in the list:
    *   It switches the Shopee Partner view to that merchant.
    *   It queries Monday.com for stores associated with that merchant that have **"Yes [Level]"** in the check column.
    *   It determines if the store should be **OPEN** or **CLOSED** based on the "Request Close" column in Monday.com.
    *   It compares the desired state with the actual state on Shopee.
    *   If they differ (e.g., Monday says Open, Shopee says Closed), it performs the action.
    *   It verifies the action was successful via API response or UI check.
5.  **Reporting**: After processing a merchant, a summary is sent to the configured Discord channel.

## How to Use

### Prerequisites
- Python 3.x installed.
- Required Python packages installed (`pip install -r requirements.txt`).
- `.env` file configured with:
    - `MONDAY_API_KEY`: Your Monday.com API key.
    - `DISCORD_WEBHOOK_URL`: Webhook URL for notifications.
    - Shopee credentials (if managed via `.env` or `credentials.py`).

### Running the Automation
**Method 1: Batch File (Recommended)**
Double-click **`run_force_open_scheduler.bat`**. This will open a command window and keep it running.

**Method 2: Command Line**
Open a terminal in the project root (`sf-automation`) and run:
```bash
python shopee_scrapper/force_open_scheduler.py
```

## Configuration & Adjustments

### Adjusting the Schedule
Open `shopee_scrapper/force_open_scheduler.py` and modify the constants at the top:
```python
INTERVAL_MINUTES = 15  # How often to run (in minutes)
```

### Changing Run Mode (Headless / Dry Run)
Open `shopee_scrapper/force_open_scheduler.py`:
- **Headless Mode**: Set `HEADLESS_MODE = False` if you want to see the browser window (useful for debugging).
- **Dry Run**: Set `DRY_RUN = True` to simulate the process without actually clicking the Open/Close buttons.
```python
SCALE_LEVEL = 1       # Monday.com filter level
DRY_RUN = False       # True = Simulation only
HEADLESS_MODE = True  # True = No visible browser
```

### Adding/Removing Merchants
1.  **Processing List**: Merchants are defined in `shopee_scrapper/config/settings.py` (variable `MERCHANT_PROCESSING_LIST`).
2.  **Monday.com Mapping**: If adding a new merchant, you must also add their Monday.com column IDs to `shopee_scrapper/force_open.py`:
    ```python
    MERCHANT_COL_MAP = {
        "NewMerchant": "monday_column_id_here",
        ...
    }
    ```

### Debugging
- **Logs**: Check the console output for real-time progress.
- **Screenshots**: If an action fails, screenshots are saved in `shopee_scrapper/debug_screenshots`.
- **HTML Dumps**: HTML source code of failed pages is saved in `shopee_scrapper/debug_html`.
