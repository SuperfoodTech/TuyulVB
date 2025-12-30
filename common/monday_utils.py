"""
Monday.com utility functions for common operations.
Consolidates Monday API helper functions across all scripts.
"""

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
    log.info(f"Fetching items from board {board_id}...")

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

        log.info(f"Successfully fetched {len(items)} items from board {board_id}.")
        return items
    except Exception as e:
        log.error(f"Failed to fetch items from board {board_id}: {e}")
        return []
