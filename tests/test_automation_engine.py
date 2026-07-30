"""
Unit tests for Tahap 2: Core Automation Engine, Priority Matrix Enforcement, and Audit Logging.
"""

import os
import sys
import unittest
import tempfile
from datetime import datetime

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.data_provider import LocalJsonDataProvider, OutletData, BaseDataProvider
from common.db_manager import DatabaseManager
from modules.shopee.force_open.refactored import run_force_open


class TestAutomationEnginePriorityEnforcement(unittest.TestCase):

    def setUp(self):
        self.temp_json = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_json.close()

        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()

        # Initialize mock sample outlets
        self.sample_data = [
            {
                "store_id": "ST_AUTO_OPEN",
                "merchant_id": "M01",
                "outlet_long_name": "Store Auto Open",
                "outlet_short_name": "AutoOpenStore",
                "operating_days": "1,2,3,4,5,6,7",
                "open_time": "00:00",
                "close_time": "23:59",
                "vercel_toggle": True,
                "shopee_toggle_last": False,  # Store is currently OFF -> Needs Auto Open
                "suspension_status": False,
                "subscription_status": "Active"
            },
            {
                "store_id": "ST_AUTO_CLOSE_SUSPENDED",
                "merchant_id": "M02",
                "outlet_long_name": "Store Suspended",
                "outlet_short_name": "SuspendedStore",
                "operating_days": "1,2,3,4,5,6,7",
                "open_time": "00:00",
                "close_time": "23:59",
                "vercel_toggle": True,
                "shopee_toggle_last": True,  # Store is currently OPEN -> Needs Auto Close
                "suspension_status": True,   # Suspended by Admin
                "suspension_reason": "Kewajiban pembayaran",
                "subscription_status": "Active"
            },
            {
                "store_id": "ST_AUTO_CLOSE_VERCEL_OFF",
                "merchant_id": "M03",
                "outlet_long_name": "Store Vercel OFF",
                "outlet_short_name": "VercelOffStore",
                "operating_days": "1,2,3,4,5,6,7",
                "open_time": "00:00",
                "close_time": "23:59",
                "vercel_toggle": False,      # Merchant toggled OFF
                "shopee_toggle_last": True,  # Store is currently OPEN -> Needs Auto Close
                "suspension_status": False,
                "subscription_status": "Active"
            }
        ]

        import json
        with open(self.temp_json.name, "w") as f:
            json.dump(self.sample_data, f, indent=4)

        self.provider = LocalJsonDataProvider(json_file_path=self.temp_json.name)
        self.db_manager = DatabaseManager(db_path=self.temp_db.name)

    def tearDown(self):
        if os.path.exists(self.temp_json.name):
            os.remove(self.temp_json.name)
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def test_priority_engine_decisions_and_dry_run(self):
        stats = run_force_open(
            session=None,
            data_provider=self.provider,
            dry_run=True,
            db_manager=self.db_manager
        )

        # Verify Forced Open (ST_AUTO_OPEN)
        self.assertEqual(len(stats["forced_open"]), 1)
        self.assertIn("AutoOpenStore (DRY_RUN)", stats["forced_open"])

        # Verify Forced Close (ST_AUTO_CLOSE_SUSPENDED and ST_AUTO_CLOSE_VERCEL_OFF)
        self.assertEqual(len(stats["forced_close"]), 2)

        # Verify audit logs created in DB
        logs = self.db_manager.get_connection().execute("SELECT * FROM bot_logs").fetchall()
        self.assertEqual(len(logs), 3)


if __name__ == "__main__":
    unittest.main()
