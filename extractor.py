from gsheet import GSheet
from grab_scraper import GrabScraper

if __name__ == "__main__":
    # GSheet setup
    CREDENTIALS_PATH = 'D:/Project/Intern Superfood - SQA/Experimental/sf-automation/superfood-test-429606-985b604b952a.json'
    SPREADSHEET_ID = '1K23P86B0C6n_c2a1k35IM4s3wA6h2H2o4qYc8a5f6b7'
    WORKSHEET_NAME = 'Sheet1'

    gsheet = GSheet(CREDENTIALS_PATH, SPREADSHEET_ID)
    df = gsheet.get_worksheet_as_dataframe(WORKSHEET_NAME)

    # GrabScraper setup
    DRIVER_PATH = 'D:/Project/Intern Superfood - SQA/Experimental/sf-automation/chromedriver.exe'
    scraper = GrabScraper(DRIVER_PATH)

    # Processing
    urls = []
    for index, row in df.iterrows():
        restaurant_name = row['Restaurant Name']
        location = row['Location']
        print(f"Searching for '{restaurant_name}' in '{location}'...")
        url = scraper.search_restaurant(restaurant_name, location)
        urls.append(url)
        print(f"Found URL: {url}")

    scraper.close()

    # Update GSheet
    df['Grab Food URL'] = urls
    gsheet.update_worksheet_from_dataframe(WORKSHEET_NAME, df)

    print("Scraping and updating complete.")
