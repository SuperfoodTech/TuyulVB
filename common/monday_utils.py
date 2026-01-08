"""
Monday.com utility functions for common operations.
Consolidates Monday API helper functions across all scripts.
"""

import json
import time
import logging
from common.monday_api import execute_monday_query
from common.logger import get_logger

log = get_logger("monday_utils")


def get_board_name(board_id):
    """
    Fetches the name of a board from Monday.com.

    Args:
        board_id: Monday.com board ID (integer or string)

    Returns:
        Board name string, or fallback "Board {board_id}" if fetch fails
    """
    log.info(f"Fetching board name for board ID: {board_id}...")
    query = f"query {{ boards(ids: {board_id}) {{ name }} }}"
    response = execute_monday_query(query)
    try:
        return response["data"]["boards"][0]["name"]
    except (KeyError, IndexError, TypeError) as e:
        log.error(f"Could not fetch board name for board ID {board_id}: {e}")
        return f"Board {board_id}"  # Fallback


def fetch_board_items(board_id, group_id=None, limit=500):
    """
    Fetches items from a Monday.com board with optional group filtering.

    Args:
        board_id: Monday.com board ID
        group_id: Optional group ID to filter items
        limit: Maximum items per page (default 500)

    Returns:
        List of items or empty list if fetch fails
    """
    log.debug(f"Fetching items from board {board_id}...")

    if group_id:
        query = f"""
        query {{
            boards(ids: {board_id}) {{
                groups(ids: ["{group_id}"]) {{
                    items_page(limit: {limit}) {{
                        items {{
                            id
                            name
                            column_values {{
                                id
                                text
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """
    else:
        query = f"""
        query {{
            boards(ids: {board_id}) {{
                items_page(limit: {limit}) {{
                    items {{
                        id
                        name
                        column_values {{
                            id
                            text
                        }}
                    }}
                }}
            }}
        }}
        """

    try:
        response = execute_monday_query(query)
        boards = response.get("data", {}).get("boards", [])

        if not boards:
            log.error(f"Board {board_id} not found or access denied.")
            return []

        if group_id:
            groups = boards[0].get("groups", [])
            if not groups:
                log.warning(f"Group '{group_id}' not found in board {board_id}.")
                return []
            items = groups[0].get("items_page", {}).get("items", [])
        else:
            items = boards[0].get("items_page", {}).get("items", [])

        log.debug(f"Successfully fetched {len(items)} items from board {board_id}.")
        return items
    except Exception as e:
        log.error(f"Failed to fetch items from board {board_id}: {e}")
        return []


def get_col_value(item: dict, column_id: str) -> str:
    """
    Safely extracts the text value from an item's column_values by column ID.

    Args:
        item: Monday.com item object with column_values
        column_id: Column ID to search for

    Returns:
        Column text value or empty string if not found
    """
    for col in item.get("column_values", []):
        if col.get("id") == column_id:
            return col.get("text", "")
    return ""


def get_all_items_from_group(board_id: int, group_id: str, column_ids: list) -> list:
    """
    Fetches all items from a single group on a board with pagination support.

    Implements cursor-based pagination to handle large datasets across multiple
    API calls, with proper error handling and recovery.

    Args:
        board_id: Monday.com board ID
        group_id: Monday.com group ID within the board
        column_ids: List of column IDs to retrieve

    Returns:
        List of items with their column values, or empty list on error
    """
    all_items = []
    cursor = None

    query = """
    query getItems($boardId: [ID!]!, $groupIds: [String!], $cursor: String, $columnIds: [String!]) {
        boards(ids: $boardId) {
            groups(ids: $groupIds) {
                items_page(limit: 500, cursor: $cursor) {
                    cursor
                    items { id name column_values(ids: $columnIds) { id text } }
                }
            }
        }
    }
    """

    page_count = 0
    while True:
        try:
            variables = {
                "boardId": [board_id],
                "groupIds": [group_id],
                "cursor": cursor,
                "columnIds": column_ids,
            }

            response = execute_monday_query(query, variables)

            # Check for API errors
            if not response or "errors" in response:
                error_msg = response.get("errors") if response else "No response"
                log.error(
                    f"Error fetching items for board {board_id}, group {group_id}: {error_msg}"
                )
                break

            # Navigate response structure
            groups_data = response.get("data", {}).get("boards", [])
            if not groups_data:
                log.warning(f"Board {board_id} not found or inaccessible")
                break

            groups = groups_data[0].get("groups", [])
            if not groups:
                log.warning(
                    f"Group {group_id} not found on board {board_id} or is empty"
                )
                break

            items_page = groups[0].get("items_page", {})
            if not items_page:
                break

            items = items_page.get("items", [])
            all_items.extend(items)
            page_count += 1

            log.debug(
                f"Fetched page {page_count} with {len(items)} items from group {group_id}"
            )

            # Check for more pages
            cursor = items_page.get("cursor")
            if not cursor:
                break

            time.sleep(0.5)  # Rate limiting between API calls

        except Exception as e:
            log.error(f"Exception while fetching items: {e}")
            break

    log.info(f"Successfully fetched {len(all_items)} total items from group {group_id}")
    return all_items


def update_statuses_in_bulk(
    updates: dict,
    board_id: int,
    column_id: str,
    column_title: str,
    batch_size: int = 50,
):
    """
    Updates status columns in batches to avoid API limits.

    Monday.com has complexity limits that prevent updating too many items at once.
    This function batches updates into safe chunks.

    Args:
        updates: Dict mapping item_id -> label_value
        board_id: Monday.com board ID
        column_id: Column ID to update
        column_title: Column title (for logging)
        batch_size: Number of items to update per API call (default 50)
    """
    if not updates:
        return

    all_updates = list(updates.items())
    total_updates = len(all_updates)

    for i in range(0, total_updates, batch_size):
        batch = all_updates[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total_updates + batch_size - 1) // batch_size

        log.info(
            f"Processing batch {batch_num}/{total_batches} for column '{column_title}': {len(batch)} items..."
        )

        mutation_parts = []
        variables = {}
        variable_definitions = []

        for j, (item_id, label) in enumerate(batch):
            var_suffix = f"{i}_{j}"
            item_id_var = f"itemId{var_suffix}"
            board_id_var = f"boardId{var_suffix}"
            column_id_var = f"columnId{var_suffix}"
            value_var = f"value{var_suffix}"

            variable_definitions.extend(
                [
                    f"${item_id_var}: ID!",
                    f"${board_id_var}: ID!",
                    f"${column_id_var}: String!",
                    f"${value_var}: JSON!",
                ]
            )

            mutation_parts.append(
                f"update_{item_id.replace('-', '_')}: change_column_value("
                f"item_id: ${item_id_var}, board_id: ${board_id_var}, "
                f"column_id: ${column_id_var}, value: ${value_var}) {{ id }}"
            )

            variables.update(
                {
                    item_id_var: int(item_id),
                    board_id_var: board_id,
                    column_id_var: column_id,
                    value_var: json.dumps({"label": label}),
                }
            )

        full_mutation = f"mutation({', '.join(variable_definitions)}) {{ {' '.join(mutation_parts)} }}"
        response = execute_monday_query(full_mutation, variables)

        if response and "errors" in response:
            log.error(f"Error updating batch {batch_num}: {response['errors']}")

        if total_updates > batch_size:
            time.sleep(1)  # Rate limiting between batches
