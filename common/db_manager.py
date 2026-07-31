"""
Database Manager for Auto-OC Bot
Manages local SQLite database for backup, caching outlet snapshots, and storing structured audit logs.
"""

import os
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from common.logger import get_logger

log = get_logger("db_manager")

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "db",
    "tuyul_vb.db"
)


class DatabaseManager:
    """Handles SQLite connection, table migrations, outlet backups, and audit logging."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)
        self._ensure_db_dir()
        self.init_db()

    def _ensure_db_dir(self):
        """Ensures the directory for the database file exists."""
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        os.makedirs(db_dir, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Returns a connection to the SQLite database with row factory enabled."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Creates tables for outlet snapshots and bot logs if they do not exist."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Table for outlet backup snapshots
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS outlets (
                        store_id TEXT PRIMARY KEY,
                        merchant_id TEXT,
                        owner_name TEXT,
                        portal_name TEXT,
                        outlet_long_name TEXT,
                        outlet_short_name TEXT,
                        operating_days TEXT,
                        open_time TEXT,
                        close_time TEXT,
                        vercel_toggle INTEGER,
                        shopee_toggle_last INTEGER,
                        suspension_status INTEGER,
                        suspension_reason TEXT,
                        suspension_start TEXT,
                        suspension_end TEXT,
                        subscription_package TEXT,
                        subscription_start TEXT,
                        subscription_end TEXT,
                        subscription_total_days INTEGER,
                        subscription_status TEXT,
                        last_checked_at TEXT,
                        raw_data_json TEXT,
                        updated_at TEXT
                    )
                """)

                # Table for structured audit logs
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bot_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        store_id TEXT NOT NULL,
                        outlet_long_name TEXT,
                        outlet_short_name TEXT,
                        suspension_status INTEGER,
                        subscription_status TEXT,
                        vercel_toggle INTEGER,
                        shopee_status_before INTEGER,
                        bot_action TEXT,
                        shopee_status_after INTEGER,
                        status_result TEXT,
                        error_message TEXT,
                        admin_info TEXT
                    )
                """)
                conn.commit()
            log.info(f"Database initialized successfully at: {self.db_path}")
        except Exception as e:
            log.error(f"Failed to initialize database at {self.db_path}: {e}")

    def save_outlets_backup(self, outlets_data: List[Dict[str, Any]]) -> bool:
        """Saves or updates a snapshot of outlets in the backup database."""
        if not outlets_data:
            return False

        query = """
            INSERT INTO outlets (
                store_id, merchant_id, owner_name, portal_name, outlet_long_name, outlet_short_name,
                operating_days, open_time, close_time, vercel_toggle, shopee_toggle_last,
                suspension_status, suspension_reason, suspension_start, suspension_end,
                subscription_package, subscription_start, subscription_end, subscription_total_days,
                subscription_status, last_checked_at, raw_data_json, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            ) ON CONFLICT(store_id) DO UPDATE SET
                merchant_id = excluded.merchant_id,
                owner_name = excluded.owner_name,
                portal_name = excluded.portal_name,
                outlet_long_name = excluded.outlet_long_name,
                outlet_short_name = excluded.outlet_short_name,
                operating_days = excluded.operating_days,
                open_time = excluded.open_time,
                close_time = excluded.close_time,
                vercel_toggle = excluded.vercel_toggle,
                shopee_toggle_last = excluded.shopee_toggle_last,
                suspension_status = excluded.suspension_status,
                suspension_reason = excluded.suspension_reason,
                suspension_start = excluded.suspension_start,
                suspension_end = excluded.suspension_end,
                subscription_package = excluded.subscription_package,
                subscription_start = excluded.subscription_start,
                subscription_end = excluded.subscription_end,
                subscription_total_days = excluded.subscription_total_days,
                subscription_status = excluded.subscription_status,
                last_checked_at = excluded.last_checked_at,
                raw_data_json = excluded.raw_data_json,
                updated_at = excluded.updated_at
        """

        now_str = datetime.now().isoformat()
        rows = []
        for item in outlets_data:
            rows.append((
                str(item.get("store_id", "")),
                str(item.get("merchant_id", "")),
                str(item.get("owner_name", "")),
                str(item.get("portal_name", "")),
                str(item.get("outlet_long_name", "")),
                str(item.get("outlet_short_name", "")),
                str(item.get("operating_days", "1,2,3,4,5,6,7")),
                str(item.get("open_time", "00:00")),
                str(item.get("close_time", "23:59")),
                1 if item.get("vercel_toggle") else 0,
                1 if item.get("shopee_toggle_last") else 0,
                1 if item.get("suspension_status") else 0,
                str(item.get("suspension_reason", "")),
                str(item.get("suspension_start", "")),
                str(item.get("suspension_end", "")),
                str(item.get("subscription_package", "")),
                str(item.get("subscription_start", "")),
                str(item.get("subscription_end", "")),
                int(item.get("subscription_total_days", 0)),
                str(item.get("subscription_status", "Active")),
                str(item.get("last_checked_at", now_str)),
                json.dumps(item),
                now_str
            ))

        try:
            with self.get_connection() as conn:
                conn.executemany(query, rows)
                conn.commit()
            log.info(f"Successfully backed up {len(rows)} outlets to local database.")
            return True
        except Exception as e:
            log.error(f"Failed to save outlets backup to database: {e}")
            return False

    def get_outlets_backup(self) -> List[Dict[str, Any]]:
        """Retrieves stored outlet snapshots from the database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM outlets ORDER BY store_id ASC")
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    item = dict(row)
                    item["vercel_toggle"] = bool(item["vercel_toggle"])
                    item["shopee_toggle_last"] = bool(item["shopee_toggle_last"])
                    item["suspension_status"] = bool(item["suspension_status"])
                    result.append(item)
                return result
        except Exception as e:
            log.error(f"Failed to retrieve outlets backup from database: {e}")
            return []

    def log_action(
        self,
        store_id: str,
        outlet_long_name: str,
        outlet_short_name: str,
        suspension_status: bool,
        subscription_status: str,
        vercel_toggle: bool,
        shopee_status_before: Optional[bool],
        bot_action: str,
        shopee_status_after: Optional[bool],
        status_result: str,
        error_message: str = "",
        admin_info: str = ""
    ) -> bool:
        """Records a bot action in the database audit log."""
        query = """
            INSERT INTO bot_logs (
                timestamp, store_id, outlet_long_name, outlet_short_name,
                suspension_status, subscription_status, vercel_toggle,
                shopee_status_before, bot_action, shopee_status_after,
                status_result, error_message, admin_info
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self.get_connection() as conn:
                conn.execute(query, (
                    datetime.now().isoformat(),
                    str(store_id),
                    str(outlet_long_name),
                    str(outlet_short_name),
                    1 if suspension_status else 0,
                    str(subscription_status),
                    1 if vercel_toggle else 0,
                    1 if shopee_status_before is True else (0 if shopee_status_before is False else None),
                    str(bot_action),
                    1 if shopee_status_after is True else (0 if shopee_status_after is False else None),
                    str(status_result),
                    str(error_message),
                    str(admin_info)
                ))
                conn.commit()
            return True
        except Exception as e:
            log.error(f"Failed to insert bot audit log for store {store_id}: {e}")
            return False
