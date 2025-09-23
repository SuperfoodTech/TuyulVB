import os
import json
import logging
from collections import defaultdict
from dotenv import load_dotenv
import time

from services.base.service_factory import ServiceFactory
from services.utils.logging import setup_logging
from services.config import MONDAY_BOARD_ID, MONDAY_TARGET_GROUP_NAME, DUPLICATE_CHECKS

# --- Global Settings ---
POLL_INTERVAL_SECONDS = 600
STATE_FILE = "monday_state.json"

# --- Logging Configuration ---
setup_logging()

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

    monday_client = ServiceFactory.get_monday_client()

    target_group_id, column_map = monday_client.get_board_structure(
        MONDAY_BOARD_ID,
        MONDAY_TARGET_GROUP_NAME
    )
    if not target_group_id:
        logging.fatal(f"Could not find Group. Exiting.")
        return

    id_to_title_map = {v: k for k, v in column_map.items()}
    all_source_titles = {
        check['source']
        for check in DUPLICATE_CHECKS
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
            current_item_states = monday_client.get_all_items_and_columns(
                MONDAY_BOARD_ID, target_group_id, source_column_ids)

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

            checks_to_run = DUPLICATE_CHECKS
            if not run_full_check:
                affected_columns = changed_values_by_column.keys()
                checks_to_run = [
                    check for check in DUPLICATE_CHECKS if check['source'] in affected_columns]
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

                monday_client.update_statuses_in_bulk(
                    updates_to_perform, MONDAY_BOARD_ID, target_col_id, target_col_title)

            logging.info(f"All checks complete. Waiting for next interval.")
            known_item_states = current_item_states
            save_state_to_file(STATE_FILE, known_item_states)

        except Exception as e:
            logging.error(
                f"An unexpected error occurred in the main loop: {e}", exc_info=True)

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
