import requests
import os
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()

API_KEY = os.getenv("MONDAY_API_KEY")
API_URL = "https://api.monday.com/v2"

# ⬇️ --- Set your Board ID --- ⬇️
BOARD_ID = 2075483964

# --- Set Headers ---
headers = {
    "Authorization": API_KEY,
    "API-Version": "2024-01"
}

# --- Main execution ---
try:
    print(f"Retrieving all groups from board ID: {BOARD_ID}...")

    # This query asks for all groups on the specified board and their IDs/titles.
    query_groups = f'''
    query {{
        boards(ids: {BOARD_ID}) {{
            name
            groups {{
                id
                title
            }}
        }}
    }}
    '''

    response = requests.post(
        API_URL, json={'query': query_groups}, headers=headers)
    response.raise_for_status()

    board_data = response.json()['data']['boards'][0]
    board_name = board_data['name']
    groups = board_data['groups']

    print(
        f"\n✅ Success! Found {len(groups)} groups on board '{board_name}':\n")

    if groups:
        for group in groups:
            print(f"Group Name: {group['title']}")
            print(f"Group ID:   {group['id']}")
            print("-" * 30)
    else:
        print("No groups were found on this board.")

except Exception as e:
    print(f"❌ An unexpected error occurred: {e}")
