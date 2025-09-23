"""Minimal Monday.com client skeleton for refactor scaffolding.

This file intentionally keeps implementation light. The full client should
implement GraphQL queries, paging, rate-limit handling, and retries.
"""
import os
import requests
import time
import json
import logging
from typing import Any, Dict, Optional, List
from collections import defaultdict

from ..base.exceptions import APIError, AuthenticationError, ConfigurationError
from . import queries


class MondayClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('MONDAY_API_KEY')
        if not self.api_key:
            raise ConfigurationError('MONDAY_API_KEY not provided')
        self.endpoint = 'https://api.monday.com/v2'
        self.logger = logging.getLogger(__name__)

    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }

    def run_query(self, query: str, variables: Optional[Dict[str, Any]] = None, max_retries: int = 3, initial_wait: int = 2) -> Dict[str, Any]:
        """
        Sends a GraphQL query to the Monday.com API and handles errors,
        with exponential backoff for rate limiting.
        """
        payload = {'query': query}
        if variables:
            payload['variables'] = variables

        retries = 0
        wait_time = initial_wait

        while retries < max_retries:
            try:
                response = requests.post(
                    self.endpoint, json=payload, headers=self._headers())
                response.raise_for_status()
                data = response.json()
                if 'errors' in data:
                    self.logger.error(
                        f"GraphQL query failed with errors: {data['errors']}")
                    if 'complexity' in str(data['errors']).lower():
                        raise APIError(
                            "Complexity budget exhausted")
                return data
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    raise AuthenticationError(
                        "Unauthorized: Check your Monday.com API key.")
                if e.response.status_code == 429:
                    retries += 1
                    if retries >= max_retries:
                        self.logger.error(
                            "Max retries reached for complexity budget error. Aborting this request.")
                        raise APIError(
                            "Max retries reached for complexity budget error")

                    try:
                        error_data = e.response.json()
                        wait_time = error_data.get("extensions", {}).get(
                            "retry_in_seconds", wait_time)
                    except json.JSONDecodeError:
                        pass

                    self.logger.warning(
                        f"Complexity budget exhausted. Retrying in {wait_time} seconds... (Attempt {retries}/{max_retries})")
                    time.sleep(wait_time)
                    wait_time *= 2
                else:
                    error_content = e.response.text if e.response else "N/A"
                    self.logger.error(
                        f"API Request failed: {e} - Response: {error_content}")
                    raise APIError(f"API Request failed: {e}")
            except requests.exceptions.RequestException as e:
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
            values = {cv['id']: cv['text']
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
