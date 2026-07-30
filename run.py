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
from common.db_manager import DatabaseManager
from common.data_provider import DataProviderFactory

log = get_logger("run")


def run_health_check():
    """Verifies that all necessary config files, packages, data providers, and DB are present."""
    overall_ok = True
    log.info("=" * 80)
    log.info("=== Configuration & System Health Check ===")
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
            "setuptools": "setuptools",
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
    log.info("Checking Global & Data Provider Configurations...")
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=True)
        log.info("[OK] .env file loaded.")

    provider_type = os.getenv("DATA_PROVIDER_TYPE", "hybrid")
    log.info(f"[OK] Data Provider Type: '{provider_type}'")

    log.info("-" * 80)
    log.info("Checking Shopee Configurations...")
    check_module_vars("config.credentials_shopee", {"ACCOUNT_CREDS": dict})
    check_module_vars("config.settings_shopee", {"MERCHANT_PROCESSING_LIST": list, "DATA_PROVIDER_TYPE": str})

    log.info("-" * 80)
    log.info("Testing Data Provider & SQLite Database Backup...")
    try:
        provider = DataProviderFactory.create_provider()
        outlets = provider.fetch_all_outlets()
        log.info(f"[OK] Data Provider initialized. Loaded {len(outlets)} outlets.")
    except Exception as e:
        log.error(f"[FAIL] Data Provider initialization failed: {e}")
        overall_ok = False

    log.info("=" * 80)
    if overall_ok:
        log.info("[OK] System Health check passed cleanly!")
    else:
        log.error("[FAIL] Health check failed. Please fix the issues listed above.")


def inspect_live_outlets():
    """CLI Inspector to view registered outlets, Vercel Toggles, and 5-level priority decisions."""
    log.info("=" * 90)
    log.info("=== LIVE OUTLET STATUS INSPECTOR ===")
    log.info("=" * 90)

    try:
        provider = DataProviderFactory.create_provider()
        outlets = provider.fetch_all_outlets()
        if not outlets:
            log.warning("No outlets found in Data Provider.")
            return

        header = f"{'Store ID':<10} | {'Outlet Name':<25} | {'Vercel':<8} | {'Penangguhan':<12} | {'Sub. Status':<12} | {'Desired Status':<15}"
        print(header)
        print("-" * 90)
        for o in outlets:
            desired_status, reason = o.calculate_desired_shopee_status()
            desired_str = "OPEN" if desired_status else "OFF"
            susp_str = "Ya (Suspended)" if o.is_suspended() else "Tidak"
            vercel_str = "ON" if o.vercel_toggle else "OFF"
            print(f"{o.store_id:<10} | {o.outlet_short_name[:25]:<25} | {vercel_str:<8} | {susp_str:<12} | {o.subscription_status:<12} | {desired_str:<15}")
        print("=" * 90)
    except Exception as e:
        log.error(f"Failed to inspect live outlets: {e}")


def view_audit_logs():
    """Inspects recent bot audit logs stored in the local SQLite database."""
    log.info("=" * 95)
    log.info("=== SQLITE BOT AUDIT LOG INSPECTOR ===")
    log.info("=" * 95)

    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, timestamp, store_id, outlet_short_name, vercel_toggle, shopee_status_before, bot_action, shopee_status_after, status_result FROM bot_logs ORDER BY id DESC LIMIT 20")
            rows = cursor.fetchall()

        if not rows:
            log.info("No audit logs recorded yet in database.")
            return

        header = f"{'Log ID':<6} | {'Timestamp':<20} | {'Store ID':<10} | {'Action':<12} | {'Before':<8} | {'After':<8} | {'Result':<10}"
        print(header)
        print("-" * 95)
        for r in rows:
            before_str = "OPEN" if r["shopee_status_before"] == 1 else ("OFF" if r["shopee_status_before"] == 0 else "N/A")
            after_str = "OPEN" if r["shopee_status_after"] == 1 else ("OFF" if r["shopee_status_after"] == 0 else "N/A")
            print(f"{r['id']:<6} | {str(r['timestamp'])[:19]:<20} | {str(r['store_id']):<10} | {str(r['bot_action']):<12} | {before_str:<8} | {after_str:<8} | {str(r['status_result']):<10}")
        print("=" * 95)
    except Exception as e:
        log.error(f"Failed to fetch audit logs: {e}")


def run_single_bot_cycle():
    """Executes a single cycle of Auto Open & Auto Close store evaluations."""
    log.info("Executing Single Auto Open & Auto Close Bot Cycle...")
    try:
        from modules.shopee.force_open.refactored import run_force_open
        run_force_open(dry_run=False)
    except Exception as e:
        log.error(f"Error during single bot cycle execution: {e}")


MENU_ITEMS = [
    {"name": "Run Health Check", "action": run_health_check, "is_script": False},
    {"name": "Inspect Live Outlet Statuses & Priority Matrix", "action": inspect_live_outlets, "is_script": False},
    {"name": "Inspect SQLite Bot Audit Logs (bot_logs)", "action": view_audit_logs, "is_script": False},
    {"name": "Run Single Auto Open / Auto Close Cycle", "action": run_single_bot_cycle, "is_script": False},
    {
        "name": "Shopee: Login Setup & Session Runner",
        "path": os.path.join("modules", "shopee", "main_runner.py"),
        "cwd": os.path.join(PROJECT_ROOT, "modules", "shopee"),
        "args": ["--task", "extract_raw"],
        "is_script": True,
        "description": "Interactive runner for Shopee login setup and session initialization.",
    },
    {
        "name": "Shopee: Automated Force Open Scheduler",
        "path": os.path.join("modules", "shopee", "force_open", "scheduler.py"),
        "cwd": PROJECT_ROOT,
        "is_script": True,
        "description": "Automated scheduler for force opening/closing Shopee stores based on Vercel Toggle & Priority Engine.",
    },
]


def display_menu():
    print("\n" + "=" * 80)
    print("=== FoodMaster Auto Open & Auto Close Bot Suite ===")
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

            if selected_item.get("is_script", False):
                script_path = os.path.join(PROJECT_ROOT, selected_item["path"])
                working_dir = selected_item.get("cwd", PROJECT_ROOT)
                script_args = selected_item.get("args", [])
                log.info(f"Executing script: {selected_item['name']}")

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
                except subprocess.CalledProcessError as e:
                    log.error(f"Script '{selected_item['name']}' failed with exit code {e.returncode}.")
            else:
                selected_item["action"]()

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
