import requests
import json
import os
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()

API_KEY = os.getenv("MONDAY_API_KEY")
API_URL = "https://api.monday.com/v2"
BOARD_ID = 2075992045

# Confirmed Group ID for "S1"
GROUP_ID = "new_group29179"

# --- Set Headers ---
headers = {
    "Authorization": API_KEY,
    "API-Version": "2024-01"
}

# --- Data to be written ---
merchant_data = {
    "merchantID": "6-C7A1LUKKLJW2HE",
    "merchantName": "Ayam Lada Hitam, Foodnesia - Kedungkandang",
    "address": "Perum Oma View Blok Gi No. 41, Jl. Bandara Abdurrahman Saleh (Geprek 41, Dekat Huget Malang Tour), Cemorokandang, Kedungkandang, Malang, 65138",
    "status": "ACTIVE"
}

# --- Main execution ---
try:
    # --- STEP 1: Fetch column IDs from the board ---
    print("Fetching board structure to get column IDs...")
    query_columns = f'query {{ boards(ids: {BOARD_ID}) {{ columns {{ id title }} }} }}'
    response = requests.post(
        API_URL, json={'query': query_columns}, headers=headers)
    response.raise_for_status()

    board_data = response.json()
    columns = board_data['data']['boards'][0]['columns']

    # Create a mapping from column titles to their actual IDs
    column_map = {col['title']: col['id'] for col in columns}
    print("Successfully mapped column names to IDs.")

    # --- STEP 2: Prepare the data and execute the mutation ---
    # The 'Name' column is populated by this 'item_name' variable
    item_name = merchant_data['merchantName']

    # ⬇️ --- CORRECTED MAPPING --- ⬇️
    # The other columns are populated here.
    column_values = {
        column_map["Name"]: merchant_data["merchantName"],
        column_map["Store ID"]: merchant_data["merchantID"],
        column_map["Address"]: merchant_data["address"],
        column_map["Outlet Status"]: {"label": merchant_data["status"]}
    }

    column_values_json = json.dumps(column_values)

    mutation_query = """
    mutation ($boardId: ID!, $groupId: String!, $itemName: String!, $columnValues: JSON!) {
      create_item (
        board_id: $boardId,
        group_id: $groupId,
        item_name: $itemName,
        column_values: $columnValues
      ) {
        id
        name
      }
    }
    """

    variables = {
        'boardId': BOARD_ID,
        'groupId': GROUP_ID,
        'itemName': item_name,
        'columnValues': column_values_json
    }

    print(f"Sending data to create new item in group 'S1'...")
    mutation_response = requests.post(
        API_URL, json={'query': mutation_query, 'variables': variables}, headers=headers)
    mutation_response.raise_for_status()

    result_data = mutation_response.json()

    if 'errors' in result_data:
        print("❌ API Error during mutation:")
        for error in result_data['errors']:
            print(f"- {error['message']}")
    else:
        new_item = result_data['data']['create_item']
        print("\n✅ Success! New item created on Monday.com:")
        print(f"  - Item ID: {new_item['id']}")
        print(f"  - Item Name: {new_item['name']}")

except requests.exceptions.HTTPError as http_err:
    print(f"❌ HTTP error occurred: {http_err}")
    print(f"   Response Text: {http_err.response.text}")
except KeyError as key_err:
    print(f"❌ Key Error: A column name in the script does not match a column on your board.")
    print(f"   Could not find the column named: {key_err}")
except Exception as e:
    print(f"❌ An unexpected error occurred: {e}")
