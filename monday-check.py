import requests
import json
import os
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
API_KEY = os.getenv("MONDAY_API_KEY")
API_URL = "https://api.monday.com/v2"

# --- Check if API Key is set ---
if not API_KEY:
    raise ValueError(
        "❌ MONDAY_API_KEY not found. Please set it in your .env file.")

# --- Set Headers ---
headers = {
    "Authorization": API_KEY,
    "Content-Type": "application/json"  # Good practice to include
}

# --- Main execution ---
try:
    print("Connecting to Monday.com API to fetch all boards...")

    all_boards = []
    page = 1
    # The API's max limit per page is 100
    limit = 100

    while True:
        # Define the GraphQL Query with page and limit variables
        query = f'{{ boards(page: {page}, limit: {limit}) {{ id name }} }}'
        data = {'query': query}

        response = requests.post(API_URL, json=data, headers=headers)
        response.raise_for_status()
        response_data = response.json()

        if 'errors' in response_data:
            print("❌ API Error:")
            for error in response_data['errors']:
                print(f"- {error['message']}")
            break  # Exit loop on error

        boards_on_this_page = response_data['data']['boards']

        # If the API returns an empty list, we've reached the last page
        if not boards_on_this_page:
            break

        # Add the boards from this page to our main list
        all_boards.extend(boards_on_this_page)

        # Go to the next page for the next loop iteration
        page += 1

    print(
        f"\n✅ Success! Found a total of {len(all_boards)} available boards:\n")
    for board in all_boards:
        print(f"Board Name: {board['name']}")
        print(f"Board ID:   {board['id']}")
        print("-" * 30)

# --- Error Handling ---
except requests.exceptions.HTTPError as http_err:
    print(f"❌ HTTP error occurred: {http_err}")
    print(f"   Status Code: {response.status_code}")
    print(f"   Response Text: {response.text}")
except requests.exceptions.RequestException as req_err:
    print(f"❌ An error occurred during the request: {req_err}")
except Exception as e:
    print(f"❌ An unexpected error occurred: {e}")
