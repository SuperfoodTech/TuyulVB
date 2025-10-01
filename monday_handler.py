import os
import json
import time
import requests
from tqdm import tqdm
from utils import log, is_network_available


def execute_monday_query(query, variables=None):
    """Safely executes a GraphQL query to the Monday.com API."""
    monday_api_key = os.getenv("MONDAY_API_KEY")
    if not monday_api_key:
        log("fatal", "MONDAY_API_KEY not found in .env file.")
        return None

    monday_api_url = "https://api.monday.com/v2"
    headers = {"Authorization": monday_api_key, "API-Version": "2023-07"}

    payload = {'query': query}
    if variables:
        payload['variables'] = variables

    try:
        response = requests.post(
            monday_api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log("error", f"Monday API request failed: {e}")
        return None


def write_to_monday_one_by_one(merchants_list, board_id, group_id, api_type):
    """Writes merchants to Monday.com, handling network errors and conditional columns."""
    log("info",
        f"Connecting to Monday.com board: {board_id}, group: {group_id}...")

    query_columns = f'query {{ boards(ids: {board_id}) {{ columns {{ id title }} }} }}'
    response_data = execute_monday_query(query_columns)
    if not response_data or 'data' not in response_data:
        log("error", "Could not fetch board structure. Check board ID and API key.")
        return
    column_map = {col['title']: col['id']
        for col in response_data['data']['boards'][0]['columns']}

    log("info",
        f"Starting to write {len(merchants_list)} merchants to Monday.com...")

    for merchant in tqdm(merchants_list, desc="Uploading Merchants"):
        item_name = merchant.get('merchantName', 'N/A')
        column_values = {column_map.get(
            "Store ID"): merchant.get("merchantID")}

        if api_type == 'MULTI_OUTLET' and "Outlet Status" in column_map:
            status_value = merchant.get("status")
            if status_value:
                column_values[column_map["Outlet Status"]] = {
                    "label": status_value}

        column_values = {k: v for k, v in column_values.items() if k and v}
        mutation_query = """
        mutation ($boardId: ID!, $groupId: String!, $itemName: String!, $columnValues: JSON!) {
            create_item (board_id: $boardId, group_id: $groupId, item_name: $itemName, column_values: $columnValues) { id }
        }"""
        variables = {'boardId': board_id, 'groupId': group_id,
            'itemName': item_name, 'columnValues': json.dumps(column_values)}

        while True:
            response_data = execute_monday_query(mutation_query, variables)
            if response_data is None:
                log("warn", "API call failed. Pausing until network is restored...")
                while not is_network_available():
                    log("error", "Network is down. Re-checking in 30 seconds...")
                    time.sleep(30)
                log("success", "Network restored. Retrying failed item.")
                continue
            if "errors" in response_data:
                log("error",
                    f"API error for '{item_name}': {response_data['errors'][0]['message']}. Skipping.")
            break
    log("success", "Finished uploading process for this group.")
                    f"API error for '{item_name}': {response_data['errors'][0]['message']}. Skipping.")
            break
    log("success", "Finished uploading process for this group.")
