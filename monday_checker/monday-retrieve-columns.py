import os
import sys
import requests
import json
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.monday_api import MONDAY_API_KEY, API_URL, execute_monday_query

# --- Configuration ---
load_dotenv()

# --- DO NOT EDIT BELOW THIS LINE ---
API_URL = "https://api.monday.com/v2"
HEADERS = {"Authorization": MONDAY_API_KEY, "API-Version": "2023-10"}


def find_column_ids(board_id):
    """Fetches and prints all column names and IDs for a specific board."""
    print(f"Fetching columns for board {board_id}...")
    query = f"query {{ boards(ids: {board_id}) {{ columns {{ id title }} }} }}"
    try:
        response = requests.post(API_URL, json={"query": query}, headers=HEADERS)
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            print(f"🔴 ERROR: Could not fetch board. Response: {result['errors']}")
            return

        columns = result["data"]["boards"][0]["columns"]

        print("\n--- Columns on Your Board ---")
        for col in columns:
            print(f"- Name: '{col['title']}', ID: '{col['id']}'")
        print("-----------------------------\n")

    except requests.exceptions.RequestException as e:
        print(f"🔴 A network error occurred: {e}")
    except KeyError:
        print("🔴 ERROR: Could not parse the board data. Is the Board ID correct?")


# --- MAIN SCRIPT ---
if __name__ == "__main__":
    if not MONDAY_API_KEY:
        print("🔴 ERROR: MONDAY_API_KEY not found in your .env file.")
    else:
        # --- Get Board ID from user ---
        while True:
            try:
                board_id_input = input("Please enter the Monday.com Board ID: ")
                board_id = int(board_id_input)
                break
            except ValueError:
                print("🔴 Invalid input. Please enter a numeric Board ID.")
        find_column_ids(board_id)
