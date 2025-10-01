# 🤖 Grab Food Data Extractor 🤖

A powerful and efficient automation tool designed to extract key data for restaurants from Grab Food and update your Google Sheets. Say goodbye to manual searching!

## ✨ What It Does

This project provides a seamless pipeline to enrich your restaurant database. It automates the tedious task of finding key restaurant data from Grab Food.

The core workflow is as follows:

1.  **📖 Read Data**: The script securely connects to your Google Sheet and reads a list of restaurant names and their locations.
2.  **🌐 Scrape Web**: For each restaurant, it launches a browser, navigates to Grab Food, and performs a search using the provided details.
3.  **🔗 Extract Data**: Once the correct restaurant is found, it captures key information:
    *   The internal **Grab Store ID**.
    *   The actual **Outlet Name**
    *   The current **Outlet Status** (e.g., Open, Closed).
4.  **✍️ Update Sheet**: The script then populates the corresponding columns in your original Google Sheet with the extracted data. If a restaurant isn't found, it's gracefully marked as "Not Found".

This automation saves countless hours of manual work, reduces human error, and keeps your data up-to-date.

## 🏗️ Project Structure

The project is organized into a modular structure for clarity, maintainability, and scalability.

```
sf-automation/
├── 📜 README.md              # You are here!
├── 📝 requirements.txt        # Project dependencies for pip.
├── 🚀 extractor.py          # The main controller that orchestrates the workflow.
├── 📊 gsheet.py             # Module for all Google Sheets interactions.
├── 🕷️ grab_scraper.py        # Module for Selenium-based web scraping of Grab Food.
├── 🔑 superfood-test-....json # Your Google API credentials file.
└── 🚗 chromedriver.exe       # The Selenium WebDriver for Chrome.
```

-   `extractor.py`: The heart of the operation. It initializes the scraper and sheet modules and manages the flow of data between them.
-   `gsheet.py`: A dedicated class `GSheet` that handles authentication and data transactions (reading/writing) with the Google Sheets API.
-   `grab_scraper.py`: Contains the `GrabScraper` class, which encapsulates all the web scraping logic using Selenium. It handles browser control, navigation, and data extraction.

## 🚀 How to Deploy

Follow these steps to get the extractor up and running on your local machine.

### 1. Prerequisites

-   **Python 3.x**: Make sure you have Python installed.
-   **Google Chrome**: The scraper uses Chrome, so it must be installed.
-   **Google Cloud Project**: A project with the Google Sheets API enabled.

### 2. Installation & Setup

1.  **Clone the Repository**:
    ```bash
    # If this were a git repository
    git clone <your-repo-url>
    cd sf-automation
    ```

2.  **Create a Virtual Environment (Recommended)**: Using a virtual environment keeps your project dependencies isolated.
    ```bash
    # Create the environment
    python -m venv venv

    # Activate it
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies**: This project's dependencies are listed in `requirements.txt`. Install them all with one command:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Google Sheets API Credentials**:
    -   Go to your Google Cloud Console.
    -   Create a **Service Account**.
    -   Download the credentials as a `JSON` file.
    -   **Important**: Share your Google Sheet with the `client_email` found in the JSON file, giving it "Editor" permissions.
    -   Place the downloaded JSON file in the project directory.

5.  **Chrome WebDriver**:
    -   Check your Google Chrome version (`Settings > About Chrome`).
    -   Download the matching version of **ChromeDriver** from the official site.
    -   Place `chromedriver.exe` in the project directory.

### 3. Configuration

Open `extractor.py` and update the constants at the top of the `if __name__ == "__main__":` block:

```python
# extractor.py
CREDENTIALS_PATH = 'path/to/your/credentials.json'
SPREADSHEET_ID = 'your_google_sheet_id_from_its_url'
WORKSHEET_NAME = 'Sheet1' # The name of the tab in your sheet
DRIVER_PATH = 'path/to/your/chromedriver.exe'
```

## 🧪 How to Test

1.  **Prepare Your Google Sheet**: Ensure your sheet has columns for both input and output.
    *   **Input Columns**: `Restaurant Name`, `Location` (should be filled with data).
    *   **Output Columns**: `Store ID`, `Outlet Status` (will be populated by the script).

2.  **Run the Extractor**: Open your terminal or command prompt, navigate to the project directory, and execute the script:
    ```bash
    python extractor.py
    ```

3.  **Monitor the Console**: The script will print its progress, showing which restaurant it's currently searching for.

4.  **Verify the Output**: Once the script finishes, check your Google Sheet. The `Store ID` and `Outlet Status` columns should now be populated with the results!

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
*This project was crafted to bring efficiency and automation to your data enrichment tasks.*
