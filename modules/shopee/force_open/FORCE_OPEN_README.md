# Shopee Force Open Automation (Refactored / Hybrid API)

## 📖 Overview

This automation suite manages the opening and closing of Shopee Food stores based on triggers from a Monday.com board.

**Key Features:**
*   **Hybrid Architecture:** Uses Selenium *only* for initial secure authentication, then switches to high-speed internal API calls for all store operations.
*   **Performance:** Capable of processing hundreds of stores in seconds using parallel execution.
*   **Reliability:** Auto-recovers from session timeouts and handles merchant switching automatically.
*   **Reporting:** Sends detailed summaries of actions taken (Open/Close/Skipped) to Discord.

---

## 🛠️ Setup Guide

Follow these steps to get the automation running from scratch.

### 1. Prerequisites

*   **Operating System:** Windows (preferred for the provided `.bat` scripts), macOS, or Linux.
*   **Python:** Version 3.10 or higher.
*   **Google Chrome:** Must be installed (the automation uses the standard Chrome browser).
*   **Git:** To clone the repository.

### 2. Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd sf-automation
    ```

2.  **Install Dependencies:**
    Open a terminal in the project root and run:
    ```bash
    pip install -r requirements.txt
    ```

### 3. Environment Configuration (`.env`)

Create a file named `.env` in the root directory (`sf-automation/.env`). You can copy `.env.example` as a starting point.

**Required Variables:**
```env
# Your Monday.com Personal API Key
MONDAY_API_KEY=your_monday_api_key_here

# Discord Webhook URL for notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url_here

# (Optional) Shopee Credentials if you want to automate the login fully
# If not provided, you may need to scan the QR code manually on first run
SHOPEE_EMAIL=your_shopee_email
SHOPEE_PASSWORD=your_shopee_password
```

### 4. Monday.com Board Setup

The automation relies on specific columns in your Monday.com board to function.

**Target Board:** `Klikit Migration - FWL` (ID: `5025182611`)

**Required Columns:**

| Column Name | Type | Purpose | Column ID (in Code) |
| :--- | :--- | :--- | :--- |
| **Check Status** | Status | Trigger. Must be set to **"Yes [Level]"** (e.g., "Yes 1") for the row to be processed. | `color_mkyfabkn` |
| **Request Close** | Status | Logic. If set to **"Closed"**, script forces close. Otherwise, it forces open. | `color_mkz76gas` |
| **Merchant (Long)** | Text | The Store Name exactly as it appears in Shopee. | *(Mapped in Config)* |
| **Merchant (Short)** | Text | A shorter name for logging/notifications. | *(Mapped in Config)* |
| **Store ID** | Text | **[CRITICAL]** The unique Shopee Entity ID/Store ID. | *(Mapped in Config)* |

> **💡 Tip:** You can use the scripts in `monday_checker/` to find Column IDs for your board if you need to change them.

### 5. Project Configuration (`config/settings_shopee.py`)

This file controls *which* merchants are processed and how they map to Monday.com columns.

**Key Settings:**

*   **`MERCHANT_PROCESSING_LIST`**: The list of merchants to cycle through.
    ```python
    MERCHANT_PROCESSING_LIST = [
        {
            "click_name": "SuperFood",   # Name to click in Shopee Dropdown
            "validate_name": "SuperFood", # Text to validate switch success
            "output_name": "Foodnesia",   # Internal name used for Monday mapping
        },
        ...
    ]
    ```

*   **`MONDAY_BOARD_ID`**: ID of the board to read from.

---

## 🚀 How to Use

### Method 1: The "Set and Forget" Scheduler (Recommended)

This runs the automation continuously every 15 minutes.

1.  Navigate to the project root folder.
2.  Double-click **`run_force_open_scheduler.bat`**.
3.  A command window will open.
    *   It will launch a **Headless Chrome** browser (invisible by default).
    *   If it's the very first time and you aren't logged in, you might need to change `HEADLESS_MODE = False` in `scheduler.py` to log into manually, or use the run.py and choose extract raw data for manual setup on selenium_profiles
4.  Leave this window open. It will print logs for every run.

### Method 2: Manual Run (One-Off)

If you want to trigger a single run immediately without waiting for the scheduler:

```bash
python modules/shopee/force_open/scheduler.py
```
*(Note: This runs the scheduler entry point, which triggers an immediate run upon start.)*

---

## ⚙️ Advanced Configuration

### Tweak Performance

In `modules/shopee/force_open/refactored.py`:

*   **`MAX_PARALLEL_STORES = 2`**: Controls how many stores are updated simultaneously. Increase to 3-5 for faster results if your internet is stable.
*   **`DRY_RUN = False`**: Set to `True` to simulate actions (logs only) without actually changing store status.

### Adjust Schedule Frequency

In `modules/shopee/force_open/scheduler.py`:

*   **`INTERVAL_MINUTES = 15`**: Change this value to run more or less frequently.

---

## ❓ Troubleshooting

### "Browser appears to be logged in, but tob_token cookie not found"
*   **Cause:** The script couldn't find the authentication cookie on the "Business Hours" page.
*   **Fix:** The scheduler usually retries automatically. If it fails repeatedly, the Shopee UI might have changed, or the account was logged out. Restart the `run_force_open_scheduler.bat` script.

### "Store not found in search results"
*   **Cause:** The **Store ID** or **Store Name** in Monday.com doesn't match Shopee's records.
*   **Fix:**
    1.  Go to Shopee Partner Portal manually.
    2.  Find the store.
    3.  Copy its exact name and ID.
    4.  Update the Monday.com row.

### "Failed to switch merchant"
*   **Cause:** The `click_name` in `MERCHANT_PROCESSING_LIST` doesn't match the text in the Shopee dropdown menu.
*   **Fix:** Inspect the Shopee dropdown HTML and ensure the text in `settings_shopee.py` matches *exactly*.

### "Fatal error in scheduler"
*   **Cause:** Often due to missing dependencies or incorrect file paths.
*   **Fix:** Ensure you are running the script from the **root directory** (`sf-automation/`) so that python can find the `common/` and `modules/` folders.
