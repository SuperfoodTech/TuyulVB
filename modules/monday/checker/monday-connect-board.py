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
    raise ValueError("❌ MONDAY_API_KEY not found. Please set it in your .env file.")

# --- Set Headers ---
headers = {"Authorization": API_KEY}

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

    # --- Define the GraphQL Query ---
    # This query is now simplified to only fetch the board's name and ID.
    query = f"""
    query {{
      boards(ids: [{BOARD_ID}]) {{
        id
        name
      }}
    }}
    """
    data = {"query": query}

    print(f"Attempting to connect to board ID: {BOARD_ID}...")
    response = requests.post(API_URL, json=data, headers=headers)
    response.raise_for_status()

    response_data = response.json()

    if "errors" in response_data:
        print("❌ API Error:")
        for error in response_data["errors"]:
            print(f"- {error['message']}")

    else:
        boards = response_data["data"]["boards"]
        if not boards:
            print(
                f"❌ Board with ID {BOARD_ID} not found or you don't have permission to view it."
            )
        else:
            board = boards[0]
            board_name = board["name"]
            print(
                f"\n✅ Success! Successfully connected to board: '{board_name}' (ID: {board['id']})"
            )

# --- Error Handling ---
except requests.exceptions.HTTPError as http_err:
    print(f"❌ HTTP error occurred: {http_err}")
    print(f"   Status Code: {response.status_code}")
    print(f"   Response Text: {response.text}")
except Exception as e:
    print(f"❌ An unexpected error occurred: {e}")
