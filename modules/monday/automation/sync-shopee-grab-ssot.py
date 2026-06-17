import argparse
import sys
import os

# --- Setup Project Path ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.sync_core import run_sync_main

CONFIG_FILE_PATH = os.path.join(PROJECT_ROOT, "data", "cache", "ssot_sync_config.json")
LOGGER_NAME = "sync_ssot"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Sync full and short names for {LOGGER_NAME}.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the script without making any actual changes to the board.",
    )
    args = parser.parse_args()

    run_sync_main(CONFIG_FILE_PATH, LOGGER_NAME, dry_run=args.dry_run)