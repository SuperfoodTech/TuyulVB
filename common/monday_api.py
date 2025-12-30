import os
import requests
import time
import json
import logging
from dotenv import load_dotenv

load_dotenv()

MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
API_URL = "https://api.monday.com/v2"
HEADERS = {
    "Authorization": MONDAY_API_KEY,
    "Content-Type": "application/json",
    "API-Version": "2023-10",
}
MAX_RETRIES = 10

if not MONDAY_API_KEY:
    logging.critical(
        "FATAL: MONDAY_API_KEY not found in your .env file or it is empty."
    )
    # This will be caught by scripts that import it.


def execute_monday_query(
    query, variables=None, max_retries=MAX_RETRIES, initial_wait=5
):
    """
    Sends a GraphQL query to the Monday.com API with robust retry logic.
    Handles rate limiting, network errors, and server-side issues.
    """
    if not MONDAY_API_KEY:
        logging.error("Cannot execute Monday query: MONDAY_API_KEY is not configured.")
        return None

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    retries = 0
    wait_time = initial_wait
    is_network_error_active = False

    while retries < max_retries:
        try:
            response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
            response.raise_for_status()

            if is_network_error_active:
                logging.info("Network connection restored. Proceeding with request.")
                is_network_error_active = False

            response_json = response.json()

            # Log complexity budget information if available
            if (
                "extensions" in response_json
                and "complexity" in response_json["extensions"]
            ):
                complexity = response_json["extensions"]["complexity"]
                query_cost = complexity.get("query", "N/A")
                remaining_budget = complexity.get("after", "N/A")
                logging.info(
                    f"Monday.com query cost: {query_cost}. Budget remaining: {remaining_budget}."
                )

            if "errors" in response_json and "data" in response_json:
                # Log GraphQL errors but return the data if it exists
                logging.error(
                    f"Monday.com API returned GraphQL errors: {response_json['errors']}"
                )

            return response_json

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate Limiting
                retries += 1
                try:
                    error_data = e.response.json()
                    wait_time = error_data.get("extensions", {}).get(
                        "retry_in_seconds", wait_time
                    )
                except json.JSONDecodeError:
                    pass  # Keep existing wait_time
                logging.warning(
                    f"Complexity budget exhausted (429). Retrying in {wait_time} seconds... (Attempt {retries}/{max_retries})"
                )
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, 60)  # Exponential backoff with a cap
            else:
                error_content = e.response.text if e.response else "N/A"
                logging.error(
                    f"API Request failed with HTTP Error: {e} - Response: {error_content}"
                )
                return None  # Non-retriable HTTP error

        except requests.exceptions.RequestException as e:  # Network errors
            is_network_error_active = True
            retries += 1
            logging.warning(
                f"Network connection error ({type(e).__name__}). Retrying in {wait_time} seconds... (Attempt {retries}/{max_retries})"
            )
            time.sleep(wait_time)
            wait_time = min(wait_time * 2, 120)  # Longer backoff for network issues

    logging.error(f"Max retries ({max_retries}) reached. Aborting this request.")
    return None
