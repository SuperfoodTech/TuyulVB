import requests
import os
from dotenv import load_dotenv
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from common.monday_api import MONDAY_API_KEY

# --- Configuration ---
load_dotenv()

API_KEY = os.getenv("MONDAY_API_KEY")
API_URL = "https://api.monday.com/v2"

# --- Set Headers ---
headers = {"Authorization": MONDAY_API_KEY, "API-Version": "2024-01"}

# --- Main execution ---
try:
    # --- Get Board ID from user ---
    while True:
        try:
            board_id_input = input("Please enter the Monday.com Board ID: ")
            BOARD_ID = int(board_id_input)
            break
        except ValueError:
            print("❌ Invalid input. Please enter a numeric Board ID.")

    print(f"Retrieving all groups from board ID: {BOARD_ID}...")
    query_groups = f"""
    query {{
        boards(ids: {BOARD_ID}) {{
            name
            groups {{
                id
                title
            }}
        }}
    }}
    """

    response = requests.post(API_URL, json={"query": query_groups}, headers=headers)
    response.raise_for_status()

    board_data = response.json()["data"]["boards"][0]
    board_name = board_data["name"]
    groups = board_data["groups"]

    print(f"\n✅ Success! Found {len(groups)} groups on board '{board_name}':\n")

    if groups:
        for group in groups:
            print(f"Group Name: {group['title']}")
            print(f"Group ID:   {group['id']}")
            print("-" * 30)
    else:
        print("No groups were found on this board.")

except Exception as e:
    print(f"❌ An unexpected error occurred: {e}")
