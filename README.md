# 🤖 Grab Merchant Data Extractor 🤖

An advanced automation tool to extract merchant data directly from the Grab Merchant Portal and upload it to a Monday.com board.

## ✨ What It Does

This project automates the entire lifecycle of validating and tracking store data by integrating directly with Grab's backend APIs and Monday.com.

The core workflow is as follows:

1.  **🔐 Secure Login**: The script logs into the Grab Merchant Portal using provided account credentials.
2.  **📡 Intercept API Calls**: Instead of scraping the UI, it uses `selenium-wire` to intercept the background API calls the portal makes to fetch merchant data. This is faster and more reliable.
3.  **📊 Extract Data**: It captures a complete list of merchants, including their `merchantID`, `merchantName`, and `status`.
4.  **✍️ Update Monday.com**: The script connects to your Monday.com board and populates a specified group with the extracted merchant data.

## 🏗️ Project Structure

```
sf-automation/
├── main.py                # Main controller and execution flow
├── grab_scraper.py        # Handles browser session and API interception
├── monday_handler.py      # Manages all Monday.com API interactions
├── utils.py               # Helper functions (e.g., logging)
├── 📁 config/
│   ├── credentials.py     # Grab Portal login credentials
│   ├── settings.py        # Board, group, and API endpoint configs
│   └── .env.example       # Template for environment variables
├── README.md
└── requirements.txt
```

## 🚀 How to Deploy

### 1. Prerequisites
- **Python 3.8+**
- **Google Chrome**
- A **Monday.com** account with an API key.

### 2. Installation & Setup
1.  **Clone the Repository** and navigate into the directory.
2.  **Create a Virtual Environment**:
    ```bash
    python -m venv venv
    # On Windows: venv\Scripts\activate
    # On macOS/Linux: source venv/bin/activate
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### 3. Configuration
1.  **Environment Variables**: Create a `.env` file in the `config/` directory (copy from `config/.env.example`) and add your Monday.com API key.
2.  **Grab Credentials**: In `config/credentials.py`, add the login details for the Grab Merchant Portal accounts.
3.  **Settings**: In `config/settings.py`, configure the API endpoints and Monday.com board/group IDs.

## 🧪 How to Run
1.  **Activate your virtual environment**.
2.  **Run the Extractor**: From the project's root directory, execute the main script.
    ```bash
    python main.py
    ```
3.  **Follow the Menu**: The script will present a menu to choose which account(s) to process.
4.  **Verify the Output**: Check your Monday.com board to see the newly created items.

---
*This project was crafted to bring efficiency and automation to your data enrichment tasks.*
1.  **Environment Variables**: Rename `config/.env.example` to `config/.env` and add your Monday.com API key.
2.  **Grab Credentials**: In `config/credentials.py`, add the login details for the Grab Merchant Portal accounts.
3.  **Settings**: In `config/settings.py`, configure the API endpoints and Monday.com board/group IDs.

## 🧪 How to Run
1.  **Activate your virtual environment**.
2.  **Run the Extractor**: From the project's root directory, execute the main script.
    ```bash
    python main.py
    ```
3.  **Follow the Menu**: The script will present a menu to choose which account(s) to process.
4.  **Verify the Output**: Check your Monday.com board to see the newly created items.

---
*This project was crafted to bring efficiency and automation to your data enrichment tasks.*
    python -m src.main
    ```
3.  **Follow the Menu**: The script will present a menu to choose which account(s) to process.
4.  **Verify the Output**: Check your Monday.com board to see the newly created items.

---
*This project was crafted to bring efficiency and automation to your data enrichment tasks.*
    -   **Important**: Share your Google Sheet with the `client_email` found in the JSON file, giving it "Editor" permissions.
    -   Place the downloaded JSON file in the `credentials` directory.

5.  **Chrome WebDriver**:
    -   Check your Google Chrome version (`Settings > About Chrome`).
    -   Download the matching version of **ChromeDriver** from the official site.
    -   Place `chromedriver.exe` in the `drivers` directory.

### 3. Configuration

Create a `.env` file in the `config` directory with your settings:

```env
CREDENTIALS_PATH=credentials/superfood-test.json
SPREADSHEET_ID=your_google_sheet_id
WORKSHEET_NAME=Sheet1
DRIVER_PATH=drivers/chromedriver.exe
DELAY_BETWEEN_REQUESTS=2.0
MAX_RETRIES=3
```

Then update your imports in `extractor.py`:

```python
from config.settings import load_config
config = load_config()
```

## 🧪 How to Run

1.  **Activate your virtual environment**.
2.  **Run the Extractor**: From the project's root directory, execute the main script.
    ```bash
    python -m src.main
    ```
3.  **Follow the Menu**: The script will present a menu to choose which account(s) to process.
4.  **Monitor the Console**: The script will print its progress, showing which restaurant it's currently searching for.
5.  **Verify the Output**: Once the script finishes, check your Google Sheet. The `Store ID`, `Outlet Name`, and `Outlet Status` columns should now be populated with the results!

## 📦 Dependencies

This project requires specific versions of dependencies for optimal performance:
```
gspread>=5.0.0
pandas>=1.3.0
selenium>=4.0.0
```

## 🔒 Data Privacy & Rate Limiting

- **Privacy**: All data is processed locally and only exchanged between your Google Sheet and Grab Food
- **Rate Limiting**: 
  - Default delay: 2 seconds between requests
  - Maximum recommended batch: 100 restaurants per hour
  - Adjust `time.sleep()` values in `grab_scraper.py` for your needs

## 💡 Additional Information & Best Practices

-   **Input Data Quality**: The more accurate the `Restaurant Name` and `Location`, the higher the success rate.
-   **Error Handling**: The script is resilient. If a restaurant search fails, it logs "Not Found" and moves to the next one without crashing.
-   **UI Changes**: This scraper depends on the structure of the Grab Food website. If the site's layout changes significantly, the `grab_scraper.py` module may need to be updated.
-   **Rate Limiting**: The script includes small `time.sleep()` delays to mimic human behavior and avoid being blocked. For very large datasets, consider adding longer, randomized delays between requests.

### Troubleshooting

-   **`selenium.common.exceptions.SessionNotCreatedException`**: Your `chromedriver.exe` version does not match your installed Google Chrome version.
-   **`gspread.exceptions.SpreadsheetNotFound`**: The `SPREADSHEET_ID` is incorrect, or you haven't shared the sheet with the service account's email.
-   **`gspread.exceptions.WorksheetNotFound`**: The `WORKSHEET_NAME` does not exist in your spreadsheet.
-   **Restaurants are consistently "Not Found"**: The location you're providing might be too general or too specific. Try different formats (e.g., "City", "Neighborhood, City").

---
*This project was crafted to bring efficiency and automation to your data enrichment tasks.*
-   **Error Handling**: The script is resilient. If a restaurant search fails, it logs "Not Found" and moves to the next one without crashing.
-   **UI Changes**: This scraper depends on the structure of the Grab Food website. If the site's layout changes significantly, the `grab_scraper.py` module may need to be updated.
-   **Rate Limiting**: The script includes small `time.sleep()` delays to mimic human behavior and avoid being blocked. For very large datasets, consider adding longer, randomized delays between requests.

### Troubleshooting

-   **`selenium.common.exceptions.SessionNotCreatedException`**: Your `chromedriver.exe` version does not match your installed Google Chrome version.
-   **`gspread.exceptions.SpreadsheetNotFound`**: The `SPREADSHEET_ID` is incorrect, or you haven't shared the sheet with the service account's email.
-   **`gspread.exceptions.WorksheetNotFound`**: The `WORKSHEET_NAME` does not exist in your spreadsheet.
-   **Restaurants are consistently "Not Found"**: The location you're providing might be too general or too specific. Try different formats (e.g., "City", "Neighborhood, City").

---
*This project was crafted to bring efficiency and automation to your data enrichment tasks.*
