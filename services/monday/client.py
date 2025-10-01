"""Minimal Monday.com client skeleton for refactor scaffolding.

This file intentionally keeps implementation light. The full client should
implement GraphQL queries, paging, rate-limit handling, and retries.
"""
import os
import json
import time
import requests
from tqdm import tqdm
from utils.logging import log
from services.base.exceptions import ConfigurationError, ApiError


def _is_network_available():
    try:
        requests.get("https://1.1.1.1", timeout=5)
        return True
    except requests.ConnectionError:
        return False


class MondayClient:
    """Client for interacting with the Monday.com GraphQL API."""

    def __init__(self):
        self.api_key = os.getenv("MONDAY_API_KEY")
        self.api_url = "https://api.monday.com/v2"
        self.headers = {"Authorization": self.api_key,
                        "API-Version": "2023-07"}
        if not self.api_key:
            raise ConfigurationError(
                "MONDAY_API_KEY not found in environment variables.")

    def _execute_query(self, query, variables=None):
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        try:
            response = requests.post(
                self.api_url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            json_response = response.json()
            if "errors" in json_response:
                raise ApiError(
                    f"Monday API Error: {json_response['errors'][0]['message']}")
            return json_response
        except requests.exceptions.RequestException as e:
            raise ApiError(f"Monday API request failed: {e}") from e

    def get_board_columns(self, board_id):
        query = f'query {{ boards(ids: {board_id}) {{ columns {{ id title }} }} }}'
        response_data = self._execute_query(query)
        return {col['title']: col['id'] for col in response_data['data']['boards'][0]['columns']}

    def write_items(self, merchants_list, board_id, group_id, api_type):
        log("info",
            f"Connecting to Monday.com board: {board_id}, group: {group_id}...")
        try:
            column_map = self.get_board_columns(board_id)
        except ApiError as e:
            log("error", f"Could not fetch board structure: {e}")
            return

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
            mutation_query = "mutation ($boardId: ID!, $groupId: String!, $itemName: String!, $columnValues: JSON!) { create_item (board_id: $boardId, group_id: $groupId, item_name: $itemName, column_values: $columnValues) { id } }"
            variables = {'boardId': board_id, 'groupId': group_id,
                         'itemName': item_name, 'columnValues': json.dumps(column_values)}

            while True:
                try:
                    self._execute_query(mutation_query, variables)
                    break
                except ApiError as e:
                    if not _is_network_available():
                        log("warn", "Network is down. Pausing until restored...")
                        while not _is_network_available():
                            time.sleep(30)
                        log("success", "Network restored. Retrying failed item.")
                        continue
                    else:
                        log("error",
                            f"API error for '{item_name}': {e}. Skipping.")
                        break
        log("success", "Finished uploading process for this group.")
        self.logger.error(f"A network error occurred: {e}")
        raise APIError(f"A network error occurred: {e}")

        raise APIError("Query failed after multiple retries.")

    def get_board_structure(self, board_id: int, target_group_name: Optional[str] = None, target_group_id: Optional[str] = None):
        """Fetches the board's layout."""
        variables = {'boardId': board_id}
        data = self.run_query(queries.GET_BOARD_STRUCTURE_QUERY, variables)

        if not data or not data.get('data', {}).get('boards'):
            self.logger.error("Could not fetch board structure.")
            return None, None

        board_data = data['data']['boards'][0]
        column_map = {col['title']: col['id'] for col in board_data['columns']}

        if target_group_id:
            return target_group_id, column_map

        if target_group_name:
            found_group_id = next(
                (g['id'] for g in board_data['groups'] if g['title'] == target_group_name), None)
            return found_group_id, column_map

        return None, column_map

    def get_all_items_and_columns(self, board_id: int, group_id: str, column_ids: List[str]):
        """Fetches specified column values and the item name for all items in the target group."""
        variables = {"boardId": [board_id], "groupId": [
            group_id], "columnIds": column_ids}
        data = self.run_query(queries.GET_ALL_ITEMS_QUERY, variables)

        if not data or not data.get('data', {}).get('boards'):
            self.logger.error(f"Error fetching items: {data.get('errors')}")
            return {}

        items_data = data['data']['boards'][0]['groups'][0]['items_page']['items']
        processed_items = {}
        for item in items_data:
            values = {
                cv['id']: cv['text']
                or "" for cv in item['column_values']}
            values['item_name'] = item.get('name', '')
            processed_items[item['id']] = values
        return processed_items

    def update_statuses_in_bulk(self, updates: Dict[str, str], board_id: int, column_id: str, column_title: str):
        """Updates item statuses in batches to avoid the API's token limit."""
        if not updates:
            return
        BATCH_SIZE = 50
        all_updates = list(updates.items())
        total_updates = len(all_updates)
        for i in range(0, total_updates, BATCH_SIZE):
            batch = all_updates[i:i + BATCH_SIZE]
            self.logger.info(
                f"Processing batch {i//BATCH_SIZE + 1} for column '{column_title}': {len(batch)} items...")

            mutation_parts, variables, variable_definitions = [], {}, []
            for j, (item_id, label) in enumerate(batch):
                item_id_var, board_id_var, column_id_var, value_var = f"itemId{j}", f"boardId{j}", f"columnId{j}", f"value{j}"
                variable_definitions.extend(
                    [f"${item_id_var}: ID!", f"${board_id_var}: ID!", f"${column_id_var}: String!", f"${value_var}: JSON!"])
                mutation_parts.append(
                    f"update_{item_id.replace('-', '_')}: change_column_value(item_id: ${item_id_var}, board_id: ${board_id_var}, column_id: ${column_id_var}, value: ${value_var}) {{ id }}")
                variables.update({
                    item_id_var: int(item_id),
                    board_id_var: board_id,
                    column_id_var: column_id,
                    value_var: json.dumps({"label": label})
                })

            full_mutation = f"mutation({', '.join(variable_definitions)}) {{ {' '.join(mutation_parts)} }}"
            self.run_query(full_mutation, variables)

            if total_updates > BATCH_SIZE:
                time.sleep(1)
