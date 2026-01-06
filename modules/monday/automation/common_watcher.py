import json
import logging
import time
from collections import defaultdict

from common.monday_api import execute_monday_query

# --- Helper Functions (Moved from individual scripts) ---


def get_board_structure(board_id, target_group_id_val, target_group_name_val):
    """Fetches the board's layout and finds the target group ID."""
    query = f"query {{ boards(ids: {board_id}) {{ groups {{ id title }} columns {{ id title }} }} }}"
    data = execute_monday_query(query)
    if not data or "errors" in data or not data.get("data", {}).get("boards"):
        logging.error(
            f"Could not fetch board structure for board {board_id}. Response: {data}"
        )
        return None, None

    board_data = data["data"]["boards"][0]
    column_map = {col["title"]: col["id"] for col in board_data["columns"]}

    # Prioritize the group ID if provided, otherwise search by name
    if target_group_id_val:
        target_group_id = target_group_id_val
    else:
        target_group_id = next(
            (
                g["id"]
                for g in board_data["groups"]
                if g["title"] == target_group_name_val
            ),
            None,
        )

    return target_group_id, column_map


def get_all_items_and_columns(board_id, group_id, column_ids: list):
    """Fetches all items in the target group, implementing pagination."""
    processed_items = {}
    cursor = None
    query = """
    query getItems($boardId: [ID!]!, $groupId: [String]!, $columnIds: [String!], $cursor: String) {
        boards(ids: $boardId) {
            groups(ids: $groupId) {
                items_page(limit: 500, cursor: $cursor) {
                    cursor
                    items { id name column_values(ids: $columnIds) { id text } }
                }
            }
        }
    }
    """
    while True:
        variables = {
            "boardId": [board_id],
            "groupId": [group_id],
            "columnIds": column_ids,
            "cursor": cursor,
        }
        data = execute_monday_query(query, variables)

        # Check for a complete failure first (data is None), then check for API-level errors.
        if not data:
            logging.error(
                "Error fetching items page: API request failed and returned no data."
            )
            return processed_items

        if "errors" in data or not data.get("data", {}).get("boards"):
            logging.error(f"Error fetching items page. API Response: {data}")
            return processed_items

        groups_data = data["data"]["boards"][0].get("groups", [])
        if not groups_data:
            logging.warning(
                f"Group ID '{group_id}' not found on board '{board_id}' or is empty. It may have been deleted. Skipping fetch for this cycle."
            )
            return processed_items

        items_page_data = groups_data[0].get("items_page")
        if not items_page_data:
            break

        for item in items_page_data.get("items", []):
            values = {cv["id"]: cv["text"] or "" for cv in item["column_values"]}
            values["item_name"] = item.get("name", "")
            processed_items[item["id"]] = values

        cursor = items_page_data.get("cursor")
        if not cursor:
            break
        time.sleep(0.5)

    return processed_items


def update_statuses_in_bulk(
    updates: dict, board_id: int, column_id: str, column_title: str
):
    """Updates status columns in batches to avoid API limits."""
    if not updates:
        return
    BATCH_SIZE = 50
    all_updates = list(updates.items())
    total_updates = len(all_updates)
    for i in range(0, total_updates, BATCH_SIZE):
        batch = all_updates[i : i + BATCH_SIZE]
        logging.info(
            f"Processing batch {i//BATCH_SIZE + 1} for column '{column_title}': {len(batch)} items..."
        )
        mutation_parts, variables, variable_definitions = [], {}, []
        for j, (item_id, label) in enumerate(batch):
            var_suffix = f"{i}_{j}"
            item_id_var, board_id_var, column_id_var, value_var = (
                f"itemId{var_suffix}",
                f"boardId{var_suffix}",
                f"columnId{var_suffix}",
                f"value{var_suffix}",
            )
            variable_definitions.extend(
                [
                    f"${item_id_var}: ID!",
                    f"${board_id_var}: ID!",
                    f"${column_id_var}: String!",
                    f"${value_var}: JSON!",
                ]
            )
            mutation_parts.append(
                f"update_{item_id.replace('-', '_')}: change_column_value(item_id: ${item_id_var}, board_id: ${board_id_var}, column_id: ${column_id_var}, value: ${value_var}) {{ id }}"
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
        execute_monday_query(full_mutation, variables)
        if total_updates > BATCH_SIZE:
            time.sleep(1)


def load_state_from_file(filepath: str) -> dict:
    """Loads the last known state of the board from a file."""
    try:
        with open(filepath, "r") as f:
            logging.info(f"Loaded previous state from {filepath}")
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logging.info(
            "State file not found or invalid. A full board scan will run on first execution."
        )
        return {}


def save_state_to_file(filepath: str, state: dict):
    """Saves the current state of the board to a file."""
    with open(filepath, "w") as f:
        json.dump(state, f)


# --- Main Watcher Logic (Generalized) ---


def run_watcher_loop(
    board_id,
    duplicate_checks,
    target_group_id_val,
    target_group_name_val,
    state_file,
    poll_interval,
    duplicate_label="Duplicate",
    unique_label="Unique",
):
    """The main loop for watching a board for duplicates."""
    logging.info(f"Starting Monday.com duplicate watcher for board ID: {board_id}")

    target_group_id, column_map = get_board_structure(
        board_id, target_group_id_val, target_group_name_val
    )
    if not target_group_id:
        logging.fatal(
            f"Could not find target group '{target_group_name_val}' (or ID: {target_group_id_val}). Exiting."
        )
        return

    id_to_title_map = {v: k for k, v in column_map.items()}
    all_source_titles = {check["source"] for check in duplicate_checks}
    source_column_ids = [
        column_map[t] for t in all_source_titles if t != "Name" and t in column_map
    ]

    logging.info(f"Successfully connected. Watching group ID: '{target_group_id}'.")
    known_item_states = load_state_from_file(state_file)

    while True:
        try:
            current_item_states = {}
            # Handle both single string and list of strings for group IDs
            groups_to_scan = (
                target_group_id
                if isinstance(target_group_id, list)
                else [target_group_id]
            )
            logging.info(f"Scanning {len(groups_to_scan)} group(s)...")
            for group_id in groups_to_scan:
                logging.info(f"Fetching items from group: {group_id}")
                items_in_group = get_all_items_and_columns(
                    board_id, group_id, source_column_ids
                )
                current_item_states.update(items_in_group)

            if not current_item_states and known_item_states:
                logging.warning(
                    "Failed to fetch current items from board. Skipping this cycle."
                )
                time.sleep(poll_interval)
                continue

            changed_values_by_column = defaultdict(set)
            run_full_check = False

            if len(known_item_states) != len(current_item_states):
                logging.info(
                    "Item count changed. A full check is required for consistency."
                )
                run_full_check = True

            for item_id, current_values in current_item_states.items():
                known_values = known_item_states.get(item_id, {})
                if not run_full_check and current_values != known_values:
                    for key, current_val in current_values.items():
                        old_val = known_values.get(key)
                        if old_val != current_val:
                            source_title = (
                                "Name"
                                if key == "item_name"
                                else id_to_title_map.get(key)
                            )
                            if source_title in all_source_titles:
                                if old_val:
                                    changed_values_by_column[source_title].add(
                                        old_val.strip().lower()
                                    )
                                if current_val:
                                    changed_values_by_column[source_title].add(
                                        current_val.strip().lower()
                                    )

            if not changed_values_by_column and not run_full_check:
                logging.info(
                    "No changes detected in monitored source columns. No action needed."
                )
            else:
                if run_full_check:
                    checks_to_run = duplicate_checks
                    logging.info(
                        f"Running all {len(checks_to_run)} checks due to item count change."
                    )
                else:
                    affected_columns = changed_values_by_column.keys()
                    checks_to_run = [
                        c for c in duplicate_checks if c["source"] in affected_columns
                    ]
                    logging.info(
                        f"Detected changes affecting columns: {list(affected_columns)}. Running {len(checks_to_run)} specific checks."
                    )

                for check in checks_to_run:
                    source_col_title, target_col_title = (
                        check["source"],
                        check["target"],
                    )
                    if target_col_title not in column_map:
                        logging.warning(
                            f"Target column '{target_col_title}' not found on board. Skipping check."
                        )
                        continue
                    target_col_id = column_map[target_col_title]
                    logging.info(
                        f"-> Running check: '{source_col_title}' -> '{target_col_title}'"
                    )

                    full_value_map = defaultdict(list)
                    for item_id, all_values in current_item_states.items():
                        value = ""
                        if source_col_title == "Name":
                            value = all_values.get("item_name", "").strip().lower()
                        elif source_col_title in column_map:
                            value = (
                                all_values.get(column_map[source_col_title], "")
                                .strip()
                                .lower()
                            )

                        if value:
                            full_value_map[value].append(item_id)

                    updates_to_perform = {}
                    values_to_recalculate = (
                        full_value_map.keys()
                        if run_full_check or not known_item_states
                        else changed_values_by_column.get(source_col_title, set())
                    )

                    for value in values_to_recalculate:
                        item_ids = full_value_map.get(value, [])
                        is_duplicate = len(item_ids) > 1

                        if is_duplicate and duplicate_label:
                            for item_id in item_ids:
                                updates_to_perform[item_id] = duplicate_label
                        elif not is_duplicate and unique_label is not None:
                            for item_id in item_ids:
                                updates_to_perform[item_id] = unique_label

                    update_statuses_in_bulk(
                        updates_to_perform, board_id, target_col_id, target_col_title
                    )

            logging.info("All checks completed.")
            known_item_states = current_item_states
            save_state_to_file(state_file, known_item_states)

        except Exception as e:
            logging.error(
                f"An unexpected error occurred in the main loop: {e}", exc_info=True
            )

        logging.info(f"Waiting for {poll_interval} seconds before next check...")
        time.sleep(poll_interval)
