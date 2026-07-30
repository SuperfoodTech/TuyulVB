"""
Monday.com API Client Wrapper
Handles GraphQL queries to Monday.com API v2 with graceful fallback.
"""

import os
import requests
from typing import Any, Dict, Optional
from common.logger import get_logger
from common.config import EnvConfig

log = get_logger("monday_api")

MONDAY_API_URL = "https://api.monday.com/v2"


def execute_monday_query(query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes a GraphQL query/mutation against Monday.com API v2.
    Returns the response JSON dictionary.
    """
    api_key = os.environ.get("MONDAY_API_KEY", EnvConfig.MONDAY_API_KEY)
    if not api_key or api_key.startswith("your_"):
        log.warning("MONDAY_API_KEY is missing or unconfigured. Skipping Monday.com operation.")
        return {"data": {}, "warnings": ["MONDAY_API_KEY not configured"]}

    headers = {
        "Authorization": api_key.strip(),
        "Content-Type": "application/json"
    }

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    try:
        response = requests.post(MONDAY_API_URL, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log.error(f"Error executing Monday.com API query: {e}")
        return {"data": {}, "error": str(e)}
