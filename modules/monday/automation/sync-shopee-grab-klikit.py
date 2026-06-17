import argparse
import sys
import os
import json
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Setup Project Path ---
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.sync_core import run_sync_main, execute_batch_update
from common.monday_utils import get_all_items_from_group, get_col_value

CONFIG_FILE_PATH = os.path.join(
    PROJECT_ROOT, "data", "cache", "klikit_sync_config.json"
)
LOGGER_NAME = "sync_klikit"


def validate_addresses(dry_run=False):
    """
    Validates addresses after sync.
    Matches Source SID -> Target SID.
    Checks if Target Item Name is in Source Address.
    """
    log = logging.getLogger(LOGGER_NAME)
    log.info("\n=== Starting Address Validation Step ===")

    try:
        with open(CONFIG_FILE_PATH, "r") as f:
            config = json.load(f)
    except Exception as e:
        log.error(f"Failed to load config file {CONFIG_FILE_PATH} for validation: {e}")
        return

    target_board_id = config.get("target_board_id")
    target_group_id = config.get("target_group_id")
    validation_mappings = config.get("validation_map", [])
    sync_mappings = config.get("sync_map", [])

    if not validation_mappings:
        log.warning("No 'validation_map' found in config. Skipping validation.")
        return

    # Build a map of Name -> SID Config from sync_map
    sid_config = {}
    for sm in sync_mappings:
        sid_config[sm["name"]] = {
            "source_sid_col": sm.get("source_sid_col"),
            "target_sid_col": sm.get("target_sid_col"),
        }

    # 1. Fetch Target Items (Name + all target addr/status cols + target SIDs)
    target_cols = set()
    for m in validation_mappings:
        addr_col = m.get("target_addr_col")
        if isinstance(addr_col, dict):
            target_cols.update(addr_col.values())
        elif addr_col:
            target_cols.add(addr_col)

        status_col = m.get("target_status_col")
        if isinstance(status_col, dict):
            target_cols.update(status_col.values())
        elif status_col:
            target_cols.add(status_col)

        m_name = m["name"]
        if m_name in sid_config:
            sid_col = sid_config[m_name].get("target_sid_col")
            if isinstance(sid_col, dict):
                target_cols.update(sid_col.values())
            elif sid_col:
                target_cols.add(sid_col)

    log.info(
        f"Fetching Target Items from Board {target_board_id}, Group {target_group_id}..."
    )
    target_items = get_all_items_from_group(
        target_board_id, target_group_id, list(target_cols)
    )
    log.info(f"Found {len(target_items)} target items.")

    # 2. Fetch Source Items
    source_lookups = {}

    def fetch_source_mapping(m):
        m_name = m["name"]
        sid_info = sid_config.get(m_name)
        if not sid_info or not sid_info["source_sid_col"]:
            return m_name, {}

        source_sid_col = sid_info["source_sid_col"]
        items = get_all_items_from_group(
            m["source_board_id"],
            m["source_group_id"],
            [m["source_addr_col"], source_sid_col],
        )
        lookup = {}
        for item in items:
            sid = str(get_col_value(item, source_sid_col) or "").strip()
            addr = str(get_col_value(item, m["source_addr_col"]) or "").strip()
            if sid:
                lookup[sid] = addr
        return m_name, lookup

    log.info("Fetching Source Data...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(fetch_source_mapping, m) for m in validation_mappings
        ]
        for future in as_completed(futures):
            m_name, lookup = future.result()
            source_lookups[m_name] = lookup

    # 3. Validation Logic
    updates_queue = []

    log.info("Validating Addresses...")
    for item in target_items:
        item_id = item["id"]
        item_name = str(item.get("name") or "").strip()
        updates_to_make = {}

        for m in validation_mappings:
            m_name = m["name"]
            sid_info = sid_config.get(m_name)
            if not sid_info or not sid_info["target_sid_col"]:
                continue

            target_sid_col_def = sid_info["target_sid_col"]
            source_map = source_lookups.get(m_name, {})

            # --- THE FIX: Create a list of all matches found for this mapping ---
            matches_to_process = []

            if isinstance(target_sid_col_def, dict):
                # Check ALL 4 columns, do NOT break
                for k, col_id in sorted(target_sid_col_def.items()):
                    val = str(get_col_value(item, col_id) or "").strip()
                    if val and val in source_map:
                        suffix = k.split("_")[-1]
                        matches_to_process.append((val, suffix))
            else:
                # Standard 1-to-1 fallback
                val = str(get_col_value(item, target_sid_col_def) or "").strip()
                if val and val in source_map:
                    matches_to_process.append((val, None))

            # --- Process EVERY match found (whether it's 1 or 4) ---
            for match_val, matched_suffix in matches_to_process:
                source_addr = source_map[match_val]

                # Resolve Target Columns dynamically
                actual_status_col = m["target_status_col"]
                if isinstance(actual_status_col, dict) and matched_suffix:
                    actual_status_col = actual_status_col.get(
                        f"target_status_col_{matched_suffix}"
                    )

                actual_addr_col = m["target_addr_col"]
                if isinstance(actual_addr_col, dict) and matched_suffix:
                    actual_addr_col = actual_addr_col.get(
                        f"target_addr_col_{matched_suffix}"
                    )

                current_status = str(
                    get_col_value(item, actual_status_col) or ""
                ).strip()
                if current_status in [
                    'Keep it "as is"',
                    "Keep it As is",
                    "Change Requested",
                ]:
                    continue

                base_name = item_name.split(" - ")[0]

                def get_tokens(text):
                    if not text:
                        return set()
                    cleaned = re.sub(r"[^a-z0-9]", " ", text.lower())
                    return set(cleaned.split())

                name_tokens = get_tokens(base_name)
                addr_tokens = get_tokens(source_addr)

                if not name_tokens:
                    is_valid = False
                else:
                    is_valid = name_tokens.issubset(addr_tokens)

                new_status = "Valid" if is_valid else "Invalid"
                current_addr = get_col_value(item, actual_addr_col)

                def normalize_text(t):
                    if not t:
                        return ""
                    return " ".join(str(t).replace("\xa0", " ").split())

                # Push to updates dictionary utilizing the specific resolved actual_addr_col
                if (normalize_text(source_addr) != normalize_text(current_addr)) or (
                    new_status != current_status
                ):
                    if actual_addr_col:
                        updates_to_make[actual_addr_col] = source_addr
                    if actual_status_col:
                        updates_to_make[actual_status_col] = {"label": new_status}

        if updates_to_make:
            updates_queue.append((item_id, item_name, updates_to_make))

    # 4. Execute Updates
    if updates_queue:
        log.info(f"Queuing validation updates for {len(updates_queue)} items...")
        BATCH_SIZE = 25
        for i in range(0, len(updates_queue), BATCH_SIZE):
            batch = updates_queue[i : i + BATCH_SIZE]
            try:
                execute_batch_update(batch, target_board_id, dry_run)
                log.info(f"  Processed validation batch {i//BATCH_SIZE + 1}")
            except Exception as e:
                log.error(f"  !! Validation batch failed: {e}")
    else:
        log.info("No validation updates needed.")

    log.info("=== Address Validation Complete ===\n")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=f"Sync full and short names for {LOGGER_NAME}."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the script without making any actual changes to the board.",
    )

    args = parser.parse_args()

    # --- Phase 1: Synchronization ---

    logging.getLogger(LOGGER_NAME).info("=== Phase 1: Synchronization ===")

    run_sync_main(CONFIG_FILE_PATH, LOGGER_NAME, dry_run=args.dry_run)

    # --- Phase 2: Address Validation ---

    logging.getLogger(LOGGER_NAME).info("=== Phase 2: Address Validation ===")

    validate_addresses(dry_run=args.dry_run)
