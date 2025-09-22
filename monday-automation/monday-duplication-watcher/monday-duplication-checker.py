import os
import requests
import time
import json
import logging
from collections import defaultdict
from dotenv import load_dotenv

# --- Load Configuration from files ---
load_dotenv()
try:
    import settings
except ImportError:
    print("FATAL: settings.py file not found. Please create it.")
    exit()

# --- Global Settings ---
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")

if not MONDAY_API_KEY:
    print("FATAL: MONDAY_API_KEY not found in your .env file or it is empty.")
    exit()

API_URL = "https://api.monday.com/v2"
HEADERS = {
    "Authorization": MONDAY_API_KEY,
    "Content-Type": "application/json"
}
POLL_INTERVAL_SECONDS = 600
STATE_FILE = "monday_state.json"

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Helper Functions ---


def execute_monday_query(query, variables=None, max_retries=3, initial_wait=2):
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
            response = requests.post(API_URL, json=payload, headers=HEADERS)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                retries += 1
                if retries >= max_retries:
                    logging.error(
                        "Max retries reached for complexity budget error. Aborting this request.")
                    break

                try:
                    error_data = e.response.json()
                    wait_time = error_data.get("extensions", {}).get(
                        "retry_in_seconds", wait_time)
                except json.JSONDecodeError:
                    pass

                logging.warning(
                    f"Complexity budget exhausted. Retrying in {wait_time} seconds... (Attempt {retries}/{max_retries})")
                time.sleep(wait_time)
                wait_time *= 2
            else:
                error_content = e.response.text if e.response else "N/A"
                logging.error(
                    f"API Request failed: {e} - Response: {error_content}")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"A network error occurred: {e}")
            return None

    return None


def get_board_structure(board_id):
    """Fetches the board's layout."""
    query = f'query {{ boards(ids: {board_id}) {{ groups {{ id title }} columns {{ id title }} }} }}'
    data = execute_monday_query(query)
    if not data or 'errors' in data:
        logging.error("Could not fetch board structure.")
        return None, None
    board_data = data['data']['boards'][0]
    column_map = {col['title']: col['id'] for col in board_data['columns']}
    target_group_id = None
    if hasattr(settings, 'MONDAY_TARGET_GROUP_ID') and settings.MONDAY_TARGET_GROUP_ID:
        target_group_id = settings.MONDAY_TARGET_GROUP_ID
    else:
        target_group_id = next(
            (
                g['id'] for g in board_data['groups']
                if g['title'] == settings.MONDAY_TARGET_GROUP_NAME), None)
    return target_group_id, column_map


def get_all_items_and_columns(board_id, group_id, column_ids: list):
    """Fetches specified column values and the item name for all items in the target group."""
    query = '''
    query getItems($boardId: [ID!]!, $groupId: [String]!, $columnIds: [String!]) {
        boards(ids: $boardId) {
            groups(ids: $groupId) {
                items_page(limit: 500) {
                    items { id name column_values(ids: $columnIds) { id text } }
                }
            }
        }
    }
    '''
    variables = {"boardId": [board_id], "groupId": [
        group_id], "columnIds": column_ids}
    data = execute_monday_query(query, variables)
    if not data or 'errors' in data or not data.get('data', {}).get('boards'):
        logging.error(f"Error fetching items: {data.get('errors')}")
        return {}
    items_data = data['data']['boards'][0]['groups'][0]['items_page']['items']
    processed_items = {}
    for item in items_data:
        values = {cv['id']: cv['text'] or "" for cv in item['column_values']}
        values['item_name'] = item.get('name', '')
        processed_items[item['id']] = values
    return processed_items


def update_statuses_in_bulk(updates: dict, board_id: int, column_id: str, column_title: str):
    """Updates item statuses in batches to avoid the API's token limit."""
    if not updates:
        return
    BATCH_SIZE = 50
    all_updates = list(updates.items())
    total_updates = len(all_updates)
    for i in range(0, total_updates, BATCH_SIZE):
        batch = all_updates[i:i + BATCH_SIZE]
        logging.info(
            f"Processing batch {i//BATCH_SIZE + 1} for column '{column_title}': {len(batch)} items...")
        mutation_parts, variables, variable_definitions = [], {}, []
        for j, (item_id, label) in enumerate(batch):
            item_id_var, board_id_var, column_id_var, value_var = f"itemId{j}", f"boardId{j}", f"columnId{j}", f"value{j}"
            variable_definitions.extend(
                [f"${item_id_var}: ID!", f"${board_id_var}: ID!", f"${column_id_var}: String!", f"${value_var}: JSON!"])
            mutation_parts.append(
                f"update_{item_id.replace('-', '_')}: change_column_value(item_id: ${item_id_var}, board_id: ${board_id_var}, column_id: ${column_id_var}, value: ${value_var}) {{ id }}")
            variables.update(
                {
                    item_id_var: int(item_id), board_id_var: board_id,
                    column_id_var: column_id, value_var: json.dumps({"label": label})}
            )
        full_mutation = f"mutation({', '.join(variable_definitions)}) {{ {' '.join(mutation_parts)} }}"
        execute_monday_query(full_mutation, variables)
        if total_updates > BATCH_SIZE:
            time.sleep(1)

# --- Functions for Persistent State ---


def load_state_from_file(filepath: str) -> dict:
    """Loads the last known board state from a local JSON file."""
    try:
        with open(filepath, 'r') as f:
            logging.info(f"Loaded previous state from {filepath}")
            return json.load(f)
    except FileNotFoundError:
        logging.info(
            "State file not found. Will perform a full board scan on first run.")
        return {}
    except json.JSONDecodeError:
        logging.warning(
            "Could not read state file. It might be corrupted. Starting fresh.")
        return {}


def save_state_to_file(filepath: str, state: dict):
    """Saves the current board state to a local JSON file."""
    with open(filepath, 'w') as f:
        json.dump(state, f)

# --- Main Watcher Logic ---


def main():
    """Main function to run the polling loop."""
    logging.info("Starting Monday.com multi-column duplicate watcher...")

    target_group_id, column_map = get_board_structure(settings.MONDAY_BOARD_ID)
    if not target_group_id:
        logging.fatal(f"Could not find Group. Exiting.")
        return

    id_to_title_map = {v: k for k, v in column_map.items()}
    all_source_titles = {
        check['source']
        for check in settings.DUPLICATE_CHECKS
    }
    source_column_ids = [
        column_map[t]
        for t in all_source_titles if t != "Name"
    ]

    logging.info(
        f"Successfully connected. Watching group ID: '{target_group_id}'.")
    known_item_states = load_state_from_file(STATE_FILE)

    while True:
        try:
            current_item_states = get_all_items_and_columns(
                settings.MONDAY_BOARD_ID, target_group_id, source_column_ids)

            if known_item_states == current_item_states:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            changed_values_by_column = defaultdict(set)
            run_full_check = False

            if len(known_item_states) != len(current_item_states):
                logging.info(
                    "New items or deleted items detected. A full check is required for consistency.")
                run_full_check = True
            else:
                for item_id, current_values in current_item_states.items():
                    known_values = known_item_states.get(item_id, {})
                    if current_values != known_values:
                        for key, current_val in current_values.items():
                            old_val = known_values.get(key)
                            if old_val != current_val:
                                source_title = 'Name' if key == 'item_name' else id_to_title_map.get(
                                    key)
                                if source_title in all_source_titles:
                                    if old_val:
                                        changed_values_by_column[source_title].add(
                                            old_val.strip().lower())
                                    if current_val:
                                        changed_values_by_column[source_title].add(
                                            current_val.strip().lower())

            if not changed_values_by_column and not run_full_check:
                logging.info(
                    "Change detected, but not in a monitored source column. No action needed.")
                known_item_states = current_item_states
                save_state_to_file(STATE_FILE, known_item_states)
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            checks_to_run = settings.DUPLICATE_CHECKS
            if not run_full_check:
                affected_columns = changed_values_by_column.keys()
                checks_to_run = [
                    check for check in settings.DUPLICATE_CHECKS if check['source'] in affected_columns]
                logging.info(
                    f"Detected targeted changes affecting columns: {list(affected_columns)}. Running {len(checks_to_run)} checks.")

            for check in checks_to_run:
                source_col_title, target_col_title = check['source'], check['target']
                target_col_id = column_map[target_col_title]
                logging.info(
                    f"-> Running check: '{source_col_title}' -> '{target_col_title}'")

                full_value_map = defaultdict(list)
                for item_id, all_values in current_item_states.items():
                    value = ""
                    if source_col_title == "Name":
                        value = all_values.get('item_name', "").strip().lower()
                    else:
                        value = all_values.get(
                            column_map[source_col_title], "").strip().lower()
                    if value:
                        full_value_map[value].append(item_id)

                updates_to_perform = {}
                values_to_recalculate = full_value_map.keys(
                ) if run_full_check else changed_values_by_column.get(source_col_title, set())

                for value in values_to_recalculate:
                    item_ids = full_value_map.get(value, [])
                    count = len(item_ids)
                    label = "Unique" if count == 1 else f"Duplicate {count}x"
                    if not item_ids and count == 0:
                        pass
                    for item_id in item_ids:
                        updates_to_perform[item_id] = label

                update_statuses_in_bulk(
                    updates_to_perform, settings.MONDAY_BOARD_ID, target_col_id, target_col_title)

            logging.info(f"All checks complete. Waiting for next interval.")
            known_item_states = current_item_states
            save_state_to_file(STATE_FILE, known_item_states)

        except Exception as e:
            logging.error(
                f"An unexpected error occurred in the main loop: {e}", exc_info=True)

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
