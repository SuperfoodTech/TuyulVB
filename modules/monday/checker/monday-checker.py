import os
import sys
import requests
import json
from dotenv import load_dotenv

# --- Setup Project Path ---
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.monday_api import MONDAY_API_KEY, execute_monday_query

# --- Configuration ---
load_dotenv()

def check_boards():
    """Fetches and displays all Monday.com boards."""
    print("\n--- Check Boards ---")
    if not MONDAY_API_KEY:
        print("❌ MONDAY_API_KEY not found. Please ensure it is set in your .env file.")
        return

    try:
        print("Connecting to Monday.com API to fetch all boards...")
        all_boards = []
        page = 1
        limit = 100

        while True:
            query = f"{{ boards(page: {page}, limit: {limit}) {{ id name }} }}"
            response_data = execute_monday_query(query)

            if not response_data:
                print("❌ API returned no data (check logs).")
                break

            if "errors" in response_data:
                print("❌ API Error:")
                for error in response_data["errors"]:
                    print(f"- {error['message']}")
                break

            boards_on_this_page = response_data["data"]["boards"]
            if not boards_on_this_page:
                break

            all_boards.extend(boards_on_this_page)
            page += 1

        print(f"\n✅ Success! Found a total of {len(all_boards)} available boards:\n")
        for board in all_boards:
            print(f"Board Name: {board['name']}")
            print(f"Board ID:   {board['id']}")
            print("-" * 30)

    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    input("\nPress Enter to return to menu...")


def retrieve_groups():
    """Retrieves and displays groups for a specific board."""
    print("\n--- Retrieve Groups ---")
    if not MONDAY_API_KEY:
        print("❌ MONDAY_API_KEY not found.")
        return

    API_URL = "https://api.monday.com/v2"
    # Keeping specific version from original script
    headers = {"Authorization": MONDAY_API_KEY, "API-Version": "2024-01"}

    try:
        while True:
            board_id_input = input("Please enter the Monday.com Board ID (or 'b' to back): ")
            if board_id_input.lower() == 'b':
                return
            try:
                board_id = int(board_id_input)
                break
            except ValueError:
                print("❌ Invalid input. Please enter a numeric Board ID.")

        print(f"Retrieving all groups from board ID: {board_id}...")
        query_groups = f"""
        query {{
            boards(ids: {board_id}) {{
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
        
        result = response.json()
        if "data" not in result or not result["data"]["boards"]:
             print("❌ No board found with that ID or permission denied.")
             return

        board_data = result["data"]["boards"][0]
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
    input("\nPress Enter to return to menu...")


def retrieve_columns():
    """Retrieves and displays columns for a specific board."""
    print("\n--- Retrieve Columns ---")
    if not MONDAY_API_KEY:
        print("❌ MONDAY_API_KEY not found.")
        return

    API_URL = "https://api.monday.com/v2"
    HEADERS = {"Authorization": MONDAY_API_KEY, "API-Version": "2023-10"}

    try:
        while True:
            board_id_input = input("Please enter the Monday.com Board ID (or 'b' to back): ")
            if board_id_input.lower() == 'b':
                return
            try:
                board_id = int(board_id_input)
                break
            except ValueError:
                print("❌ Invalid input. Please enter a numeric Board ID.")

        print(f"Fetching columns for board {board_id}...")
        query = f"query {{ boards(ids: {board_id}) {{ columns {{ id title }} }} }}"
        
        response = requests.post(API_URL, json={"query": query}, headers=HEADERS)
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            print(f"🔴 ERROR: Could not fetch board. Response: {result['errors']}")
            return

        if not result["data"]["boards"]:
             print("❌ No board found with that ID or permission denied.")
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
    except Exception as e:
        print(f"🔴 An unexpected error occurred: {e}")
    input("\nPress Enter to return to menu...")


def main():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("========================================")
        print("      MONDAY.COM CHECKER TOOL")
        print("========================================")
        print("1. Boards  (List all boards)")
        print("2. Group   (List groups in a board)")
        print("3. Columns (List columns in a board)")
        print("0. Exit")
        print("========================================")

        choice = input("Select an option: ")

        if choice == "1":
            check_boards()
        elif choice == "2":
            retrieve_groups()
        elif choice == "3":
            retrieve_columns()
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("Invalid selection. Please try again.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()
