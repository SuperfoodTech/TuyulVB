import requests
import json
import os
from dotenv import load_dotenv
from collections import defaultdict

# --- Configuration ---
load_dotenv()

API_KEY = os.getenv("MONDAY_API_KEY")
API_URL = "https://api.monday.com/v2"
BOARD_ID = 2075483964

# --- Set Headers ---
headers = {
    "Authorization": API_KEY,
    "API-Version": "2024-01"
}

# --- Main execution ---
try:
    print(
        f"Connecting to board ID: {BOARD_ID} and preparing to fetch all data...")

    all_items = []
    all_groups = []
    all_columns = []
    board_name = ""
    cursor = None
    page_number = 1

    while True:
        # The query is now updated to fetch columns on the first request
        query = f"""
        query {{
          boards(ids: [{BOARD_ID}]) {{
            # Only fetch board metadata on the first page for efficiency
            {'name groups {id title} columns {id title type}' if page_number == 1 else ''}
            
            items_page(limit: 100{', cursor: "' + cursor + '"' if cursor else ''}) {{
              cursor
              items {{
                id
                name
                group {{
                  id
                  title
                }}
              }}
            }}
          }}
        }}
        """

        data = {'query': query}
        print(f"Fetching page {page_number}...")

        response = requests.post(API_URL, json=data, headers=headers)
        response.raise_for_status()
        response_data = response.json()

        if 'errors' in response_data:
            print("❌ API Error:")
            for error in response_data['errors']:
                print(f"- {error['message']}")
            break

        board = response_data['data']['boards'][0]

        # On the first loop, get the board metadata
        if page_number == 1:
            board_name = board['name']
            all_groups = board['groups']
            all_columns = board['columns']  # <-- Store the column data

        page_items = board['items_page']['items']
        all_items.extend(page_items)

        cursor = board['items_page']['cursor']
        if not cursor:
            print("All pages fetched. No more items to retrieve.")
            break

        page_number += 1

    # --- Process and Display All Retrieved Data ---
    print(f"\n✅ Successfully retrieved data from board: '{board_name}'")

    # --- ⬇️ New Section to Display Columns ⬇️ ---
    if all_columns:
        print(f"\n## Board Columns ({len(all_columns)} found)")
        print("-" * 40)
        for column in all_columns:
            print(f"Header: \"{column['title']}\" (Type: {column['type']})")
        print("-" * 40)

    # --- Display Groups and Items as before ---
    if not all_groups:
        print("\nNo groups were found on this board.")
    else:
        items_by_group = defaultdict(list)
        for item in all_items:
            if item.get('group'):
                group_id = item['group']['id']
                items_by_group[group_id].append(item)

        print(f"\n## Board Content ({len(all_items)} total items)")
        for group in all_groups:
            group_id = group['id']
            group_title = group['title']
            items_in_group = items_by_group[group_id]

            print("\n" + "=" * 40)
            print(f"▶️ Group: {group_title} ({len(items_in_group)} items)")

            if not items_in_group:
                print("  (No tasks in this group)")
            else:
                for item in items_in_group:
                    print(f"  - Task: {item['name']} (ID: {item['id']})")

except Exception as e:
    print(f"❌ An unexpected error occurred: {e}")
