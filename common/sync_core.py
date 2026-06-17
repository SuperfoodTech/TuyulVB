import json
import logging
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure common imports work if running from this context (though usually imported)
# We assume the caller has set up sys.path, but we can double check or just import.
from common.monday_api import execute_monday_query
from common.notifications import send_discord_notification
from common.monday_utils import get_all_items_from_group, get_col_value
from common.config import EnvConfig, ConfigurationError


def build_lookup_map(items, key_col, val_cols):
    """Builds a {key: {val1: ..., val2: ...}} map from a list of items."""
    lookup_map = {}
    for item in items:
        key = get_col_value(item, key_col)
        if key:
            # We don't log duplicate warnings here to avoid threading log spam/race conditions
            # or just keep it simple.
            lookup_map[key] = {
                val_col: get_col_value(item, val_col) for val_col in val_cols
            }
            lookup_map[key]["name"] = item.get("name")
    return lookup_map


def fetch_source_data(mapping):
    """
    Fetches data for a single mapping.
    Returns (map_key, lookup_map).
    """
    cols_to_fetch = [mapping["source_sid_col"]]

    # Explicitly check type for specific columns to avoid side effects
    if mapping.get("type") == "shopee" and mapping.get("source_short_name_col"):
        cols_to_fetch.append(mapping["source_short_name_col"])

    if mapping.get("type") == "grab" and mapping.get("source_status_col"):
        cols_to_fetch.append(mapping["source_status_col"])

    # Needed if validate_addresses calls this function
    if mapping.get("source_addr_col"):
        cols_to_fetch.append(mapping["source_addr_col"])

    source_items = get_all_items_from_group(
        mapping["source_board"], mapping["source_group"], cols_to_fetch
    )

    # We build the map here
    lookup_map = build_lookup_map(
        source_items, mapping["source_sid_col"], cols_to_fetch
    )

    map_key = f"{mapping['source_board']}_{mapping['source_group']}"
    return map_key, lookup_map


def execute_batch_update(updates_batch, board_id, dry_run=False):
    """
    Executes a batch of updates using a single GraphQL mutation with aliases.
    updates_batch: list of (item_id, item_name, updates_dict)
    Returns: (success_count, failed_indices)
    """
    if not updates_batch:
        return 0, []

    if dry_run:
        return len(updates_batch), []

    mutation_parts = []
    variables = {"boardId": int(board_id) if str(board_id).isdigit() else str(board_id)}

    # Construct aliases
    for idx, (item_id, _, updates) in enumerate(updates_batch):
        # Alias: update_0, update_1, ...
        alias = f"update_{idx}"
        item_var = f"itemId_{idx}"
        vals_var = f"vals_{idx}"

        mutation_parts.append(
            f"{alias}: change_multiple_column_values(item_id: ${item_var}, board_id: $boardId, column_values: ${vals_var}) {{ id }}"
        )

        variables[item_var] = int(item_id) if str(item_id).isdigit() else str(item_id)
        variables[vals_var] = json.dumps(updates)

    # Build full query
    # $boardId is shared
    # We need to define all variables
    var_defs = ["$boardId: ID!"]
    for idx in range(len(updates_batch)):
        var_defs.append(f"$itemId_{idx}: ID!")
        var_defs.append(f"$vals_{idx}: JSON!")

    query = f"""
    mutation BatchUpdate({', '.join(var_defs)}) {{
        {' '.join(mutation_parts)}
    }}
    """

    # Execute
    result = execute_monday_query(query, variables)

    # Check for general failure
    if not result:
        raise Exception("Batch update failed (no response).")

    # Check for errors in response
    if "errors" in result:
        # In batch execution, if one fails, Monday might return errors for that one but data for others?
        # Or fail the whole thing. Monday API behavior varies.
        # But commonly, if we get "errors", we should be cautious.
        # We will count how many "data" keys we have.
        pass

    # Count successes in 'data'
    data = result.get("data", {})
    success_count = 0
    failed_indices = []

    if data:
        for key, value in data.items():
            # key is like "update_0"
            if value is not None:
                success_count += 1
            else:
                # If value is None, it failed. Extract index.
                try:
                    idx = int(key.split("_")[1])
                    failed_indices.append(idx)
                except (IndexError, ValueError):
                    pass  # Should not happen
        return success_count, failed_indices
    else:
        # If no data and errors, assume 0 success
        if "errors" in result:
            raise Exception(f"Batch returned errors: {result['errors']}")
        return 0, []


def run_sync_main(config_file_path, logger_name, dry_run=False):
    """
    Shared main execution logic for sync scripts.
    """
    # Setup Logger
    from common.logging_config import LOG_FORMAT, DATE_FORMAT

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=DATE_FORMAT)
    log = logging.getLogger(logger_name)

    # Load Config
    try:
        env_config = EnvConfig()
        env_config.validate()
        DISCORD_WEBHOOK_URL = env_config.DISCORD_WEBHOOK_URL
    except ConfigurationError as e:
        log.critical(f"Configuration error: {e}")
        sys.exit(1)

    try:
        with open(config_file_path, "r") as f:
            log.info(f"Loading sync configuration from {config_file_path}")
            config = json.load(f)
    except Exception as e:
        log.error(f"Failed to load config file {config_file_path}: {e}")
        sys.exit(1)

    # Validate Config
    required_keys = ["target_board_id", "target_group_id", "sync_map"]
    missing_keys = [k for k in required_keys if k not in config]
    if missing_keys:
        log.critical(
            f"Config file {config_file_path} is missing required keys: {missing_keys}"
        )
        log.critical(f"Available keys: {list(config.keys())}")
        sys.exit(1)

    TARGET_BOARD_ID = config["target_board_id"]
    TARGET_GROUP_ID = config["target_group_id"]
    SYNC_MAP = config["sync_map"]

    if dry_run:
        log.warning("=" * 50)
        log.warning("### SCRIPT IS RUNNING IN DRY-RUN MODE ###")
        log.warning("=" * 50)
    else:
        log.info(f"Starting sync script for {logger_name}...")

    stats = {
        "total_updates_queued": 0,
        "items_to_update": 0,
        "errors": 0,
        "items_updated_successfully": 0,
        "skipped_no_change": 0,
        "failed_items": [],
    }

    # --- Step 1: Parallel Build Lookup Maps ---
    log.info("--- Building Lookup Maps from Source Boards (Parallel) ---")
    lookup_maps = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        # Create futures for each mapping
        # We filter out duplicates by map_key first to avoid redundant fetches if SYNC_MAP has same board/group multiple times?
        # The original script looped SYNC_MAP and checked `if map_key in lookup_maps: continue`.
        # We can't easily check that inside futures.
        # So we identify unique keys first.
        unique_requests = {}
        for mapping in SYNC_MAP:
            map_key = f"{mapping['source_board']}_{mapping['source_group']}"
            if map_key not in unique_requests:
                unique_requests[map_key] = mapping

        futures = [
            executor.submit(fetch_source_data, m) for m in unique_requests.values()
        ]

        for future in as_completed(futures):
            try:
                m_key, l_map = future.result()
                lookup_maps[m_key] = l_map
                log.info(
                    f"  -> Fetched & built map for {m_key} ({len(l_map)} entries)."
                )
            except Exception as e:
                log.error(f"  !! Failed to fetch source data: {e}")
                # We might want to abort or continue? Original script would crash or log error depending on where.
                # We'll continue but this map will be missing.

    # --- Step 2: Fetch Target Items ---
    log.info(f"\n--- Fetching Target Items from Board {TARGET_BOARD_ID} ---")
    target_cols_to_fetch = set()
    for m in SYNC_MAP:
        # Handle target_sid_col being a dictionary (1-to-4), list, or string (1-to-1)
        if isinstance(m["target_sid_col"], dict):
            target_cols_to_fetch.update(m["target_sid_col"].values())
        elif isinstance(m["target_sid_col"], list):
            target_cols_to_fetch.update(m["target_sid_col"])
        else:
            target_cols_to_fetch.add(m["target_sid_col"])

        # Handle full name being a dict or string
        if isinstance(m["target_full_name_col"], dict):
            target_cols_to_fetch.update(m["target_full_name_col"].values())
        else:
            target_cols_to_fetch.add(m["target_full_name_col"])

        # Handle short name
        if "target_short_name_col" in m:
            if isinstance(m["target_short_name_col"], dict):
                target_cols_to_fetch.update(m["target_short_name_col"].values())
            else:
                target_cols_to_fetch.add(m["target_short_name_col"])

        # Handle status col
        if "target_status_col" in m:
            if isinstance(m["target_status_col"], dict):
                target_cols_to_fetch.update(m["target_status_col"].values())
            else:
                target_cols_to_fetch.add(m["target_status_col"])

    target_items = get_all_items_from_group(
        TARGET_BOARD_ID, TARGET_GROUP_ID, list(target_cols_to_fetch)
    )
    log.info(f"Found {len(target_items)} items to process in target group.")

    # --- Step 3: Compare and Queue Updates ---
    log.info(f"\n--- Processing {len(target_items)} Target Items ---")

    updates_queue = []  # List of (item_id, item_name, updates_dict)

    for item in target_items:
        item_id = item["id"]
        item_name = item["name"]
        updates_to_make = {}

        for mapping in SYNC_MAP:
            target_sid_def = mapping["target_sid_col"]
            map_key = f"{mapping['source_board']}_{mapping['source_group']}"

            # Use Exhaustive Search: Check all columns and collect matches
            matches_to_process = []

            if isinstance(target_sid_def, dict):
                # 1-to-4 Match: Check each column in the dictionary
                for key_name, col_id in sorted(target_sid_def.items()):
                    val = get_col_value(item, col_id)
                    if val:
                        found_data = lookup_maps.get(map_key, {}).get(val)
                        if found_data:
                            suffix = key_name.split("_")[-1]
                            matches_to_process.append((found_data, suffix))
            elif isinstance(target_sid_def, list):
                # Fallback for older lists if they exist
                for col_id in target_sid_def:
                    val = get_col_value(item, col_id)
                    if val:
                        found_data = lookup_maps.get(map_key, {}).get(val)
                        if found_data:
                            matches_to_process.append((found_data, None))
            else:
                # 1-to-1 Match: Standard behavior
                sid_to_match = get_col_value(item, target_sid_def)
                if sid_to_match:
                    found_data = lookup_maps.get(map_key, {}).get(sid_to_match)
                    if found_data:
                        matches_to_process.append((found_data, None))

            # Process every match found independently
            for source_data, matched_suffix in matches_to_process:

                # Full Name
                target_name_def = mapping["target_full_name_col"]
                actual_name_col = target_name_def
                if isinstance(target_name_def, dict) and matched_suffix:
                    actual_name_col = target_name_def.get(
                        f"target_name_col_{matched_suffix}"
                    )

                new_full_name = source_data.get("name", "")
                current_full_name = get_col_value(item, actual_name_col)
                if actual_name_col and new_full_name != (current_full_name or ""):
                    updates_to_make[actual_name_col] = new_full_name

                # Short Name (Shopee Only)
                if (
                    mapping.get("type") == "shopee"
                    and mapping.get("target_short_name_col")
                    and mapping.get("source_short_name_col")
                ):
                    target_short_def = mapping["target_short_name_col"]
                    actual_short_col = target_short_def
                    if isinstance(target_short_def, dict) and matched_suffix:
                        actual_short_col = target_short_def.get(
                            f"target_short_name_col_{matched_suffix}"
                        )

                    new_short_name = source_data.get(
                        mapping["source_short_name_col"], ""
                    )
                    current_short_name = get_col_value(item, actual_short_col)
                    if actual_short_col and new_short_name != (
                        current_short_name or ""
                    ):
                        updates_to_make[actual_short_col] = new_short_name

                # Status Sync (Grab Only)
                if (
                    mapping.get("type") == "grab"
                    and mapping.get("target_status_col")
                    and mapping.get("source_status_col")
                ):
                    target_status_def = mapping["target_status_col"]
                    actual_status_col = target_status_def
                    if isinstance(target_status_def, dict) and matched_suffix:
                        actual_status_col = target_status_def.get(
                            f"target_status_col_{matched_suffix}"
                        )

                    new_status = source_data.get(mapping["source_status_col"], "")
                    current_status = get_col_value(item, actual_status_col)

                    if (
                        actual_status_col
                        and new_status
                        and new_status != (current_status or "")
                    ):
                        updates_to_make[actual_status_col] = {"label": new_status}

        if updates_to_make:
            updates_queue.append((item_id, item_name, updates_to_make))
            stats["items_to_update"] += 1
            stats["total_updates_queued"] += len(updates_to_make)
        else:
            stats["skipped_no_change"] += 1

    # --- Step 4: Execute Batched Updates ---
    if updates_queue:
        log.info(f"--- Executing Updates for {len(updates_queue)} Items (Batched) ---")

        BATCH_SIZE = 25
        total_batches = (len(updates_queue) + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(0, len(updates_queue), BATCH_SIZE):
            batch = updates_queue[i : i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1

            log_prefix = "[DRY RUN] Would update" if dry_run else "Updating"
            log.info(
                f"  {log_prefix} batch {batch_num}/{total_batches} ({len(batch)} items)..."
            )

            try:
                updated_count, failed_indices = execute_batch_update(
                    batch, TARGET_BOARD_ID, dry_run
                )
                stats["items_updated_successfully"] += updated_count

                if failed_indices:
                    stats["errors"] += len(failed_indices)
                    log.error(
                        f"    !! Batch {batch_num} had {len(failed_indices)} partial failures."
                    )
                    for idx in failed_indices:
                        if 0 <= idx < len(batch):
                            itm = batch[idx]
                            stats["failed_items"].append(f"'{itm[1]}' ({itm[0]})")

            except Exception as e:
                log.error(f"    !! Batch {batch_num} failed: {e}")
                stats["errors"] += len(batch)
                for itm in batch:
                    stats["failed_items"].append(f"'{itm[1]}' ({itm[0]})")

            # Sleep slightly between batches to be nice to API
            if not dry_run:
                time.sleep(1)

    else:
        log.info("No items require updates.")

    # --- Step 5: Reporting ---
    log.info("\n--- Sync Complete ---")
    report_title = (
        "**DRY RUN** Sync Report"
        if dry_run
        else f"**Sync Completed for {logger_name}**"
    )
    summary_message = (
        f"{report_title}\n\n"
        f"- **Items to Update:** `{stats['items_to_update']}`\n"
        f"- **Total Column Updates Queued:** `{stats['total_updates_queued']}`\n"
        f"- **Items Skipped (No Change):** `{stats['skipped_no_change']}`\n"
        f"- **Errors:** `{stats['errors']}`\n"
        f"- **Items Successfully Updated:** `{stats['items_updated_successfully']}`"
    )

    if stats["failed_items"]:
        # Truncate if too long
        failed_list_str = "\n".join(stats["failed_items"][:20])
        if len(stats["failed_items"]) > 20:
            failed_list_str += f"\n...and {len(stats['failed_items']) - 20} more."
        summary_message += f"\n\n**Failed Items:**\n``` {failed_list_str} ```"

    log.info(summary_message.replace("**", "").replace("`", ""))

    send_discord_notification(
        DISCORD_WEBHOOK_URL,
        title=f"{logger_name.replace('sync_', '').upper()} Database Sync Report",
        description=summary_message,
    )
