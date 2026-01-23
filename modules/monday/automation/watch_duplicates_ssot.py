import logging
import os
import sys
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# Import the shared watcher logic
from modules.monday.automation.common_watcher import run_watcher_loop

# --- Load Configuration from files ---
load_dotenv()
try:
    from modules.monday.automation.config import dupsettings
except ImportError:
    print("FATAL: dupsettings.py file not found. Please create it.")
    exit()

# --- Global Settings ---
POLL_INTERVAL_SECONDS = 60
STATE_FILE = "monday_state_ssot.json"

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"

# --- Main Watcher Logic ---


def main():
    """Sets up and runs the watcher for the SSOT board."""
    run_watcher_loop(
        board_id=dupsettings.MONDAY_BOARD_ID_SSOT,
        duplicate_checks=dupsettings.DUPLICATE_CHECKS_SSOT,
        target_group_id_val=getattr(dupsettings, "MONDAY_TARGET_GROUP_ID_SSOT", None),
        target_group_name_val=getattr(dupsettings, "MONDAY_TARGET_GROUP_NAME_SSOT", ""),
        state_file=STATE_FILE,
        poll_interval=POLL_INTERVAL_SECONDS,
    )


if __name__ == "__main__":
    main()
