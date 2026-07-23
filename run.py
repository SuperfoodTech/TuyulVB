import os
import sys
import time
import subprocess
import logging
import textwrap
import importlib
from dotenv import load_dotenv

# --- Setup Project Path ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.logger import get_logger

log = get_logger("run")

# --- Script Definitions ---
SCRIPTS = [
    {
        "name": "Shopee: Login Setup & Session Runner",
        "path": os.path.join("modules", "shopee", "main_runner.py"),
        "cwd": os.path.join(PROJECT_ROOT, "modules", "shopee"),
        "args": ["--task", "extract_raw"],
        "description": "Interactive runner for Shopee login setup and session initialization.",
    },
    {
        "name": "Shopee: Force Open Scheduler",
        "path": os.path.join("modules", "shopee", "force_open", "scheduler.py"),
        "cwd": PROJECT_ROOT,
        "description": "Automated scheduler for force opening/closing Shopee stores based on Monday.com status.",
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
            log.info(f"[OK] {success_msg}")
            return True
        else:
            log.error(f"[FAIL] {failure_msg}")
            overall_ok = False
            return False

    def check_python_packages():
        log.info("Checking for required Python packages...")
        package_map = {
            "selenium-wire": "seleniumwire",
            "python-dotenv": "dotenv",
            "webdriver-manager": "webdriver_manager",
            "PyJWT": "jwt",
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
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            package_name = line.split("#")[0].strip()
            if not package_name:
                continue

            # Remove version pin if any for import test
            clean_pkg_name = package_name.split("<")[0].split(">")[0].split("=")[0].strip()
            module_name = package_map.get(clean_pkg_name, clean_pkg_name)
            try:
                importlib.import_module(module_name)
                log.info(f"  -> [OK] Package '{package_name}' is installed.")
            except ImportError:
                log.error(f"  -> [FAIL] Package '{package_name}' is NOT installed.")
                packages_ok = False

        if not packages_ok:
            log.warning("Missing packages detected. Please run: ./setup.sh or pip install -r requirements.txt")
            overall_ok = False

    def check_module_vars(module_path, schema):
        nonlocal overall_ok
        try:
            module = importlib.import_module(module_path)
            log.info(f"[OK] Config file for '{module_path}' imported successfully.")
            module_ok = True
            for var_name, var_type in schema.items():
                if not hasattr(module, var_name):
                    log.error(f"  -> Variable '{var_name}' is missing from '{module_path}'.")
                    module_ok = False
                    continue
                value = getattr(module, var_name)
                if not isinstance(value, var_type):
                    log.error(f"  -> Variable '{var_name}' has wrong type.")
                    module_ok = False
                    continue
                log.info(f"  -> [OK] Variable '{var_name}' is valid.")
            if not module_ok:
                overall_ok = False
            return module_ok
        except ImportError:
            log.error(f"Config file '{module_path}' is missing or contains an import error.")
            overall_ok = False
            return False

    check_python_packages()
    log.info("-" * 80)
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
    log.info("Checking Shopee Configurations...")
    check_module_vars("config.credentials_shopee", {"ACCOUNT_CREDS": dict})
    check_module_vars("config.settings_shopee", {"MERCHANT_PROCESSING_LIST": list, "MONDAY_BOARD_ID": int})
    log.info("=" * 80)
    if overall_ok:
        log.info("[OK] Health check passed! Configurations are in place.")
    else:
        log.error("[FAIL] Health check failed. Please fix the issues listed above.")


MENU_ITEMS = [
    {"name": "Run Health Check", "action": run_health_check, "is_script": False},
    *SCRIPTS,
]


def display_menu():
    print("\n" + "=" * 80)
    print("=== Shopee Force Open Automation Suite ===")
    print("=" * 80)
    for i, item in enumerate(MENU_ITEMS):
        print(f"  {i+1}. {item['name']}")
        if item.get("description"):
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
    while True:
        display_menu()
        log.setLevel(logging.CRITICAL)
        try:
            choice = int(input(f"Enter your choice (1-{len(MENU_ITEMS) + 1}): "))
            log.setLevel(logging.INFO)
            if not 1 <= choice <= len(MENU_ITEMS) + 1:
                raise ValueError

            if choice == len(MENU_ITEMS) + 1:
                log.info("Exiting runner. Goodbye!")
                break

            selected_item = MENU_ITEMS[choice - 1]

            if selected_item.get("is_script", True):
                script_path = os.path.join(PROJECT_ROOT, selected_item["path"])
                working_dir = selected_item.get("cwd", PROJECT_ROOT)
                script_args = selected_item.get("args", [])
                log.info(f"Executing: {selected_item['name']}")
            else:
                selected_item["action"]()
                input("\nPress Enter to return to the main menu...")
                continue

            print("-" * 80)
            sub_env = os.environ.copy()
            existing_pythonpath = sub_env.get("PYTHONPATH", "")
            sub_env["PYTHONPATH"] = f"{PROJECT_ROOT}{os.pathsep}{existing_pythonpath}"
            sub_env["PYTHONIOENCODING"] = "utf-8"
            sub_env["PROJECT_ROOT"] = PROJECT_ROOT

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
                log.error(f"Script '{selected_item['name']}' failed with exit code {e.returncode}.")

            print("-" * 80)
            log.setLevel(logging.CRITICAL)
            input("Press Enter to return to the main menu...")
            log.setLevel(logging.INFO)

        except (ValueError, IndexError):
            log.setLevel(logging.INFO)
            log.error("Invalid choice. Please enter a number from the menu.")
            time.sleep(2)


if __name__ == "__main__":
    main()
