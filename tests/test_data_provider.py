"""
Unit tests for Tahap 1: Data Provider Layer, Database Backup, and OutletData Schema.
"""

import os
import sys
import unittest
import tempfile
from datetime import datetime, time

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.data_provider import (
    OutletData,
    LocalJsonDataProvider,
    DatabaseDataProvider,
    HybridDataProvider,
    DataProviderFactory,
)
from common.db_manager import DatabaseManager


class TestOutletDataSchema(unittest.TestCase):

    def test_23_minimum_fields_and_defaults(self):
        data = {
            "store_id": "ST999",
            "merchant_id": "M999",
            "owner_name": "Budi Foodmaster",
            "portal_name": "Foodmaster Portal",
            "outlet_long_name": "Foodmaster Grand Indonesia",
            "outlet_short_name": "FM GI",
            "operating_days": "1,2,3,4,5,6,7",
            "open_time": "08:00",
            "close_time": "22:00",
            "vercel_toggle": True,
            "shopee_toggle_last": True,
            "suspension_status": "Tidak",
            "suspension_reason": "",
            "subscription_package": "12 Bulan",
            "subscription_start": "2026-01-01",
            "subscription_end": "2027-04-30",
            "subscription_total_days": 480,
            "subscription_status": "Active",
        }

        outlet = OutletData.from_dict(data)
        self.assertEqual(outlet.store_id, "ST999")
        self.assertEqual(outlet.merchant_id, "M999")
        self.assertEqual(outlet.outlet_short_name, "FM GI")
        self.assertFalse(outlet.is_suspended())
        self.assertTrue(outlet.is_subscription_active())

    def test_system_priority_matrix(self):
        # 1. Suspended outlet => Force OFF
        outlet_suspended = OutletData(
            store_id="ST01", merchant_id="M01", vercel_toggle=True, suspension_status=True
        )
        status, reason = outlet_suspended.calculate_desired_shopee_status()
        self.assertFalse(status)
        self.assertIn("Ditangguhkan", reason)

        # 2. Expired subscription => Force OFF
        outlet_expired = OutletData(
            store_id="ST02", merchant_id="M02", vercel_toggle=True, subscription_status="Expired"
        )
        status, reason = outlet_expired.calculate_desired_shopee_status()
        self.assertFalse(status)
        self.assertIn("Expired", reason)

        # 3. Vercel Toggle OFF => Force OFF
        outlet_toggle_off = OutletData(
            store_id="ST03", merchant_id="M03", vercel_toggle=False, suspension_status=False, subscription_status="Active"
        )
        status, reason = outlet_toggle_off.calculate_desired_shopee_status()
        self.assertFalse(status)
        self.assertIn("Vercel Toggle = OFF", reason)

        # 4. Valid criteria => Force ON
        outlet_active = OutletData(
            store_id="ST04", merchant_id="M04", vercel_toggle=True, suspension_status=False, subscription_status="Active",
            open_time="00:00", close_time="23:59"
        )
        status, reason = outlet_active.calculate_desired_shopee_status()
        self.assertTrue(status)
        self.assertIn("Vercel Toggle ON", reason)


class TestDatabaseManagerAndBackup(unittest.TestCase):

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_manager = DatabaseManager(db_path=self.temp_db.name)

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def test_save_and_retrieve_outlets_backup(self):
        sample_outlets = [
            {
                "store_id": "ST100",
                "merchant_id": "M100",
                "owner_name": "Test Owner",
                "portal_name": "Portal A",
                "outlet_long_name": "Outlet Long A",
                "outlet_short_name": "Outlet A",
                "operating_days": "1,2,3,4,5,6,7",
                "open_time": "09:00",
                "close_time": "21:00",
                "vercel_toggle": True,
                "shopee_toggle_last": False,
                "suspension_status": False,
                "subscription_status": "Active"
            }
        ]

        # Save to DB
        success = self.db_manager.save_outlets_backup(sample_outlets)
        self.assertTrue(success)

        # Retrieve from DB
        backup_items = self.db_manager.get_outlets_backup()
        self.assertEqual(len(backup_items), 1)
        self.assertEqual(backup_items[0]["store_id"], "ST100")
        self.assertTrue(backup_items[0]["vercel_toggle"])

    def test_audit_log_insertion(self):
        log_res = self.db_manager.log_action(
            store_id="ST100",
            outlet_long_name="Outlet Long A",
            outlet_short_name="Outlet A",
            suspension_status=False,
            subscription_status="Active",
            vercel_toggle=True,
            shopee_status_before=False,
            bot_action="OPEN_STORE",
            shopee_status_after=True,
            status_result="SUCCESS"
        )
        self.assertTrue(log_res)


class TestHybridDataProvider(unittest.TestCase):

    def setUp(self):
        self.temp_json = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_json.close()

        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()

        self.json_provider = LocalJsonDataProvider(json_file_path=self.temp_json.name)
        self.db_manager = DatabaseManager(db_path=self.temp_db.name)
        self.hybrid_provider = HybridDataProvider(
            primary_provider=self.json_provider, db_manager=self.db_manager
        )

    def tearDown(self):
        if os.path.exists(self.temp_json.name):
            os.remove(self.temp_json.name)
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def test_hybrid_fetch_and_auto_backup(self):
        outlets = self.hybrid_provider.fetch_all_outlets()
        self.assertTrue(len(outlets) > 0)

        # Verify auto backup in SQLite DB
        db_items = self.db_manager.get_outlets_backup()
        self.assertEqual(len(db_items), len(outlets))


if __name__ == "__main__":
    unittest.main()
