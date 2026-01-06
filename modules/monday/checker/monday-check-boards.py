import requests
import os
import sys

# --- Setup Project Path ---
# This allows the script to find the 'common' module when run from any directory.
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.monday_api import MONDAY_API_KEY, API_URL, execute_monday_query

# --- Configuration ---
# The API_KEY and API_URL are now imported from the common module.

# --- Check if API Key is set ---
if not MONDAY_API_KEY:
    print(
        "❌ MONDAY_API_KEY not found. Please ensure it is set in your .env file in the project root."
    )
    # The common module will log a critical error, but we exit here for clarity.
    exit(1)

# --- Main execution ---
try:
    print("Connecting to Monday.com API to fetch all boards...")

    all_boards = []
    page = 1
    # The API's max limit per page is 100
    limit = 100

    while True:
        # Define the GraphQL Query with page and limit variables
        query = f"{{ boards(page: {page}, limit: {limit}) {{ id name }} }}"
        response_data = execute_monday_query(query)

        if "errors" in response_data:
            print("❌ API Error:")
            for error in response_data["errors"]:
                print(f"- {error['message']}")
            break  # Exit loop on error

        boards_on_this_page = response_data["data"]["boards"]

        # If the API returns an empty list, we've reached the last page
        if not boards_on_this_page:
            break

        # Add the boards from this page to our main list
        all_boards.extend(boards_on_this_page)

        # Go to the next page for the next loop iteration
        page += 1

    print(f"\n✅ Success! Found a total of {len(all_boards)} available boards:\n")
    for board in all_boards:
        print(f"Board Name: {board['name']}")
        print(f"Board ID:   {board['id']}")
        print("-" * 30)

# --- Error Handling ---
except Exception as e:
    print(f"❌ An unexpected error occurred: {e}")
