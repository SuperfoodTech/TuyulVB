import os
import sys
import time
import json
import subprocess
import logging
import textwrap
from datetime import datetime
import importlib

# --- Setup Project Path ---
# Add the project root to the Python path. This allows scripts to be run from here
# and still find their modules (e.g., `from common.monday_api import ...`).
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
from common.logger import get_logger

# Use the centralized logger
log = get_logger("run")


# --- Script Definitions ---
# Each dictionary defines a script that can be run from the menu.
# 'path': The relative path to the script file.
# 'description': A short explanation of what the script does.
# 'cwd': (Optional) The working directory to run the script from. This is crucial
#        for scripts that rely on relative paths for config files (like credentials.py).
SCRIPTS = [
    {
        "name": "Shopee: Extract Raw Store Data",
        "path": os.path.join("shopee_scrapper", "main_runner.py"),
        "cwd": os.path.join(PROJECT_ROOT, "shopee_scrapper"),
        "args": ["--task", "extract_raw"],
    },
    {
        "name": "Shopee: Get Full Store Details",
        "path": os.path.join("shopee_scrapper", "main_runner.py"),
        "cwd": os.path.join(PROJECT_ROOT, "shopee_scrapper"),
        "args": ["--task", "sync_details"],
    },
    {
        "name": "Shopee: Get Store Short Names",
        "path": os.path.join("shopee_scrapper", "main_runner.py"),
        "cwd": os.path.join(PROJECT_ROOT, "shopee_scrapper"),
        "args": ["--task", "sync_short_names"],
    },
    {
        "name": "Shopee: Get Customer Details from Transactions",
        "path": os.path.join("shopee_scrapper", "main_runner.py"),
        "cwd": os.path.join(PROJECT_ROOT, "shopee_scrapper"),
        "args": ["--task", "sync_customers"],
    },
    {
        "name": "Grab: Get Merchant Data",
        "path": os.path.join("grab_scrapper", "monday-grab-extract.py"),
        "cwd": os.path.join(PROJECT_ROOT, "grab_scrapper"),
    },
    {
        "name": "Monday: Watch for Duplicates Board SSOT",
        "path": os.path.join("monday_automation", "watch_duplicates_ssot.py"),
        "cwd": PROJECT_ROOT,
    },
    {
        "name": "Monday: Watch for Duplicates Board VBO Naming",
        "path": os.path.join("monday_automation", "watch_duplicates_vbo.py"),
        "cwd": PROJECT_ROOT,
    },
    {
        "name": "Monday: Watch for Duplicates Board Manual Disbursement (Order ID)",
        "path": os.path.join("monday_automation", "watch_duplicates_orderid.py"),
        "cwd": PROJECT_ROOT,
    },
    {
        "name": "Monday: Input WA Numbers from Excel",
        "path": os.path.join("monday_automation", "input-wa.py"),
        "cwd": PROJECT_ROOT,
    },
    {
        "name": "Grab: Address Validation",
        "path": os.path.join("grab_scrapper", "monday-grab-address-validation.py"),
        "cwd": PROJECT_ROOT,
    },
    {
        "name": "Grab: Klikit Address Validation",
        "path": os.path.join("grab_scrapper", "sync_address_klikit_grab.py"),
        "cwd": PROJECT_ROOT,
    },
    {
        "name": "Monday: Sync Short Names (Pull -> SSOT)",
        "path": os.path.join("monday_automation", "short_name_updater.py"),
        "cwd": PROJECT_ROOT,
    },
    {
        "name": "Shopee: Address Validation",
        "path": os.path.join("shopee_scrapper", "main_runner.py"),
        "cwd": os.path.join(PROJECT_ROOT, "shopee_scrapper"),
        "args": ["--task", "address_validation"],
    },
    {
        "name": "Shopee: Klikit Address Validation",
        "path": os.path.join("shopee_scrapper", "main_runner.py"),
        "cwd": os.path.join(PROJECT_ROOT, "shopee_scrapper"),
        "args": ["--task", "klikit_validation"],
    },
    {
        "name": "Shopee: Klikit Address Validation - DRY RUN",
        "path": os.path.join("shopee_scrapper", "main_runner.py"),
        "cwd": os.path.join(PROJECT_ROOT, "shopee_scrapper"),
        "args": ["--task", "klikit_validation", "--dry-run"],
    },
    {
        "name": "Shopee: Klikit OPH Sync (Open/Closed)",
        "path": os.path.join("shopee_scrapper", "main_runner.py"),
        "cwd": os.path.join(PROJECT_ROOT, "shopee_scrapper"),
        "args": ["--task", "klikit_oph"],
    },
    {
        "name": "Shopee/Grab: Unified Klikit Sync (Address & OPH)",
        "path": os.path.join("shopee_scrapper", "main_runner.py"),
        "cwd": os.path.join(PROJECT_ROOT, "shopee_scrapper"),
        "args": ["--task", "klikit_unified"],
    },
    {
        "name": "Monday: Sync Full & Short Names (VB Database)",
        "path": os.path.join("monday_automation", "sync-shopee-grab-vbo.py"),
        "cwd": PROJECT_ROOT,
    },
    {
        "name": "Monday: Sync Full & Short Names (VB Database) - DRY RUN",
        "path": os.path.join("monday_automation", "sync-shopee-grab-vbo.py"),
        "cwd": PROJECT_ROOT,
        "args": ["--dry-run"],
    },
    {
        "name": "Monday: Sync Full & Short Names (Klikit Migration Database)",
        "path": os.path.join("monday_automation", "sync-shopee-grab-klikit.py"),
        "cwd": PROJECT_ROOT,
    },
    {
        "name": "Monday: Sync Full & Short Names (Klikit Migration Database) - DRY RUN",
        "path": os.path.join("monday_automation", "sync-shopee-grab-klikit.py"),
        "cwd": PROJECT_ROOT,
        "args": ["--dry-run"],
    },
]


def run_health_check():
    """Verifies that all necessary config files and environment variables are present."""
    overall_ok = True
    log.info("=" * 80)
    log.info("=== Configuration Health Check ===")
    log.info("=" * 80)

    def check(condition, success_msg, failure_msg):
        nonlocal overall_ok
        if condition:
            log.info(f"✅ {success_msg}")
            return True
        else:
            log.error(f"❌ {failure_msg}")
            overall_ok = False
            return False

    def check_json_file(file_path, schema):
        """Dynamically loads a JSON file and checks for required variables against a schema."""
        nonlocal overall_ok
        if not check(
            os.path.exists(file_path),
            f"JSON config file '{os.path.basename(file_path)}' found.",
            f"JSON config file '{os.path.basename(file_path)}' is missing.",
        ):
            return False

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            log.info(
                f"  -> ✅ JSON config file '{os.path.basename(file_path)}' parsed successfully.",
            )
        except json.JSONDecodeError:
            log.error(
                f"  -> ❌ JSON config file '{os.path.basename(file_path)}' is not valid JSON.",
                f"JSON config file '{os.path.basename(file_path)}' parsed successfully.",
            )
            overall_ok = False
            return False

        file_ok = True
        for key, key_schema in schema.items():
            if key not in data:
                log.error(
                    f"  -> Key '{key}' is missing from '{os.path.basename(file_path)}'.",
                )
                file_ok = False
                continue

            value = data[key]
            expected_type = (
                key_schema if isinstance(key_schema, type) else key_schema["type"]
            )

            if not isinstance(value, expected_type) or (
                expected_type in [dict, list] and not value
            ):
                log.error(
                    f"  -> Key '{key}' is empty or has the wrong type (expected non-empty {expected_type.__name__}).",
                )
                file_ok = False
                continue

            # If all checks pass for the key
            log.info(f"  -> ✅ Key '{key}' is present and valid.")

        if not file_ok:
            overall_ok = False

        return file_ok

    def check_python_packages():
        """Verifies that all required Python packages from requirements.txt are installed."""
        log.info("Checking for required Python packages...")

        # Mapping from requirements.txt name to the actual importable module name
        package_map = {
            "selenium-wire": "seleniumwire",
            "python-dotenv": "dotenv",
            "webdriver-manager": "webdriver_manager",
        }

        req_path = os.path.join(PROJECT_ROOT, "requirements.txt")
        if not check(
            os.path.exists(req_path),
            "requirements.txt file found.",
            "requirements.txt is missing. Cannot verify packages.",
        ):
            return

        with open(req_path, "r") as f:
            lines = f.readlines()

        packages_ok = True
        for line in lines:
            package_name = line.strip()
            if not package_name or package_name.startswith("#"):
                continue

            module_name = package_map.get(package_name, package_name)
            try:
                importlib.import_module(module_name)
                log.info(f"  -> ✅ Package '{package_name}' is installed.")
            except ImportError:
                log.error(f"  -> ❌ Package '{package_name}' is NOT installed.")
                packages_ok = False

        if not packages_ok:
            log.warning(
                f"Missing packages detected. Please run: pip install -r requirements.txt",
            )
            overall_ok = False

    def check_module_vars(module_path, schema):
        """Dynamically imports a module and checks for required variables against a schema."""
        nonlocal overall_ok
        try:
            module = importlib.import_module(module_path)
            log.info(f"✅ Config file for '{module_path}' imported successfully.")
            module_ok = True

            for var_name, var_schema in schema.items():
                if not hasattr(module, var_name):
                    log.error(
                        f"  -> Variable '{var_name}' is missing from the config file.",
                    )
                    module_ok = False
                    continue

                value = getattr(module, var_name)
                var_type = (
                    var_schema if isinstance(var_schema, type) else var_schema["type"]
                )

                # 1. Basic type and emptiness check
                if not isinstance(value, var_type) or (
                    var_type in [dict, list] and not value
                ):
                    log.error(
                        f"  -> Variable '{var_name}' is empty or has the wrong type (expected non-empty {var_type.__name__}).",
                    )
                    module_ok = False
                    continue

                # 2. Deeper structure validation for dicts and lists
                structure_ok = True
                if isinstance(var_schema, dict):
                    if "keys" in var_schema and not all(
                        k in value for k in var_schema["keys"]
                    ):
                        log.error(
                            f"  -> Dict '{var_name}' is missing required keys. Expected: {var_schema['keys']}.",
                        )
                        structure_ok = False
                    elif "items" in var_schema:
                        if not all(
                            isinstance(item, dict)
                            and all(k in item for k in var_schema["items"])
                            for item in value
                        ):
                            log.error(
                                f"  -> Items in list '{var_name}' are missing required keys. Expected in each item: {var_schema['items']}.",
                            )
                            structure_ok = False

                if not structure_ok:
                    module_ok = False
                    continue

                # If all checks pass
                log.info(f"  -> ✅ Variable '{var_name}' is present and valid.")

            if not module_ok:
                overall_ok = False
            return module_ok
        except ImportError:
            log.error(
                f"Config file '{module_path.replace('.', '/')}.py' is missing or contains an import error.",
            )
            overall_ok = False
            return False

    # 0. Python Packages
    check_python_packages()

    log.info("-" * 80)

    # 1. Global .env file
    log.info("Checking Global Configurations...")
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if check(os.path.exists(env_path), ".env file found.", ".env file is missing."):
        load_dotenv(dotenv_path=env_path, override=True)
        check(
            os.getenv("MONDAY_API_KEY"),
            "MONDAY_API_KEY is present.",
            "MONDAY_API_KEY is missing or empty in .env file.",
        )

    log.info("-" * 80)

    # 2. Shopee Scrapper
    log.info("Checking Shopee Scrapper Configurations...")
    check_module_vars("shopee_scrapper.config.credentials", {"ACCOUNT_CREDS": dict})
    check_module_vars(
        "shopee_scrapper.config.settings",
        {
            "MERCHANT_PROCESSING_LIST": {
                "type": list,
                "items": ["validate_name", "output_name"],
            },
            "MONDAY_BOARD_ID": int,
            "GROUP_MAPPING": dict,
        },
    )

    log.info("-" * 80)

    # 3. Grab Scrapper
    log.info("Checking Grab Scrapper Configurations...")
    check_module_vars("grab_scrapper.credentials", {"ACCOUNT_CREDS": dict})
    check_module_vars(
        "grab_scrapper.settings",
        {
            "GRAB_MERCHANT_CONFIG": {
                "type": dict,
                "keys": [
                    "login_url",
                    "logout_url",
                    "merchant_list_url",
                    "username_field_id",
                    "password_field_id",
                    "continue_after_username_xpath",
                ],
            },
            "TARGET_API_URL": str,
            "SINGLE_OUTLET_CHECK_URL": str,
            "MONDAY_BOARD_ID": int,
            "MONDAY_TARGET_GROUP": {
                "type": list,
                "items": ["source_portal", "group_id"],
            },
        },
    )

    log.info("-" * 80)

    # 4. Monday Automation - Watch Duplicates
    log.info("Checking Monday 'Watch Duplicates' Configurations...")
    check_module_vars(
        "monday_automation.config.dupsettings",
        {
            "MONDAY_BOARD_ID_SSOT": int,
            "DUPLICATE_CHECKS_SSOT": {"type": list, "items": ["source", "target"]},
            "MONDAY_BOARD_ID_VBO": int,
            "DUPLICATE_CHECKS_VBO": {"type": list, "items": ["source", "target"]},
        },
    )

    log.info("-" * 80)

    # 5. Monday Automation - Short Name Updater
    log.info("Checking Monday 'Short Name Updater' Configurations...")
    check(
        os.getenv("DISCORD_WEBHOOK_URL"),
        "DISCORD_WEBHOOK_URL is present for notifications.",
        "DISCORD_WEBHOOK_URL is missing. Notifications will be skipped.",
    )

    log.info("-" * 80)

    # 5. Monday Automation - Input WA
    log.info("Checking Monday 'Input WA' Configurations...")
    excel_path = os.path.join(PROJECT_ROOT, "S1 Database Mitra - Cluster 1 FWL+D.xlsx")
    check(
        os.path.exists(excel_path),
        "Excel file 'S1 Database Mitra - Cluster 1 FWL+D.xlsx' found.",
        "The required Excel file for the WA input script is missing.",
    )

    log.info("-" * 80)

    # 6. Monday Automation - VBO Sync
    log.info("Checking Monday 'VBO Sync' Configurations...")
    check_json_file(
        os.path.join(
            PROJECT_ROOT, "monday_automation", "config", "vbo_sync_config.json"
        ),
        {
            "target_board_id": int,
            "target_group_id": str,
            "sync_map": {
                "type": list,
                # A deeper check could be added here if needed
            },
        },
    )
    log.info("-" * 80)

    # 7. Shopee - Address Validation
    log.info("Checking Shopee 'Address Validation' Configurations...")
    check_module_vars(
        "shopee_scrapper.addressettings",
        {
            "SOURCE_BOARD_ID": int,
            "TARGET_BOARD_ID": int,
            "MATCH_BOARD_ID": int,
            "GROUP_MAPPING": dict,
            "TARGET_COL_STORE_ID": str,
            "TARGET_COL_ADDRESS_STATUS": str,
            "TARGET_COL_ADDRESS": str,
            "MATCH_COL_STORE_ID": str,
            "MATCH_COL_ADDRESS": str,
        },
    )
    # 6. Grab - Address Validation
    log.info("Checking Grab 'Address Validation' Configurations...")
    check_module_vars("monday_checker.credentials", {"ACCOUNT_CREDS": dict})
    check_module_vars(
        "monday_checker.valsettings",
        {
            "SOURCE_BOARD_ID": int,
            "DESTINATION_BOARD_ID": int,
            "MONDAY_SID_COLUMN_MAP": dict,
        },
    )
    check_module_vars(
        "grab_scrapper.settings",
        {
            "GRAB_MERCHANT_CONFIG": dict,
            "MONDAY_TARGET_GROUP": list,
        },
    )

    log.info("=" * 80)
    if overall_ok:
        log.info("✅ Health check passed! All configurations seem to be in place.")
    else:
        log.error("❌ Health check failed. Please fix the issues listed above.")


MENU_ITEMS = [
    {"name": "Run Health Check", "action": run_health_check, "is_script": False},
    *SCRIPTS,
]


def display_menu():
    """Prints the main menu to the console."""
    print("\n" + "=" * 80)
    print("=== Automation Suite Master Runner ===")
    print("=" * 80)
    for i, item in enumerate(MENU_ITEMS):
        print(f"  {i+1}. {item['name']}")
        if item.get("description"):  # pyright: ignore[reportUnnecessaryIsInstance]
            wrapped_desc = textwrap.fill(
                item["description"],
                width=75,
                initial_indent="     ",
                subsequent_indent="     ",
            )
            print(wrapped_desc)
    print("-" * 80)
    print(f"  {len(MENU_ITEMS) + 1}. Exit")
    print("=" * 80)


def main():
    """Main function to display the menu and run the selected script."""
    while True:
        display_menu()
        # Temporarily disable logging while waiting for user input
        log.setLevel(logging.CRITICAL)
        try:
            choice = int(input(f"Enter your choice (1-{len(MENU_ITEMS) + 1}): "))
            # Re-enable logging after input is received
            log.setLevel(logging.NOTSET)
            if not 1 <= choice <= len(MENU_ITEMS) + 1:
                raise ValueError

            if choice == len(MENU_ITEMS) + 1:
                log.info("Exiting the master runner. Goodbye!")
                break

            selected_item = MENU_ITEMS[choice - 1]

            if selected_item.get("is_script", True):
                script_path = os.path.join(PROJECT_ROOT, selected_item["path"])
                working_dir = selected_item.get("cwd", PROJECT_ROOT)
                script_args = selected_item.get("args", [])
                log.info(f"Executing script: {selected_item['name']}")
            else:
                # Disable logging during the action if it's interactive
                log.setLevel(logging.CRITICAL)
                selected_item["action"]()
                log.setLevel(logging.NOTSET)
                input("\nPress Enter to return to the main menu...")
                continue

            print("-" * 80)
            sub_env = os.environ.copy()
            existing_pythonpath = sub_env.get("PYTHONPATH", "")
            sub_env["PYTHONPATH"] = f"{PROJECT_ROOT}{os.pathsep}{existing_pythonpath}"
            sub_env["PYTHONIOENCODING"] = "utf-8"
            sub_env["PROJECT_ROOT"] = PROJECT_ROOT  # Pass the project root to the child

            command = [sys.executable, "-u", script_path] + script_args
            try:
                process = subprocess.Popen(command, cwd=working_dir, env=sub_env)
                return_code = process.wait()

                if return_code == 0:
                    log.info(f"✅ Finished executing: {selected_item['name']}")
                else:
                    raise subprocess.CalledProcessError(return_code, process.args)

            except KeyboardInterrupt:
                log.warning(f"Script '{selected_item['name']}' interrupted by user.")
                process.terminate()
                process.wait()

            except subprocess.CalledProcessError as e:
                log.error(
                    f"Script '{selected_item['name']}' failed with exit code {e.returncode}.",
                )
            except subprocess.TimeoutExpired:
                log.error(
                    f"Script '{selected_item['name']}' timed out after {selected_item['timeout']} seconds and was terminated.",
                )

            print("-" * 80)
            log.setLevel(logging.CRITICAL)
            input("Press Enter to return to the main menu...")
            log.setLevel(logging.NOTSET)

        except (ValueError, IndexError):
            log.setLevel(logging.NOTSET)  # Re-enable logging on error
            log.error("Invalid choice. Please enter a number from the menu.")
            time.sleep(2)


if __name__ == "__main__":
    main()
