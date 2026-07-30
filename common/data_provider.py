"""
Data Provider Module for TuyulVB
Provides unified data access layer for ShopeeFood Outlets, supporting:
1. Google Sheets Database
2. Vercel Dashboard API
3. SQLite Database Backup & Cache
4. Hybrid Failover Mode
5. Local JSON Dev Fallback
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, time
from typing import List, Dict, Any, Optional

import requests
from common.logger import get_logger
from common.db_manager import DatabaseManager

log = get_logger("data_provider")


@dataclass
class OutletData:
    """Represents the complete data schema of a ShopeeFood outlet (23 minimum required fields)."""
    store_id: str
    merchant_id: str
    owner_name: str = ""
    portal_name: str = ""
    outlet_long_name: str = ""
    outlet_short_name: str = ""
    operating_days: str = "1,2,3,4,5,6,7"  # 1=Monday, 7=Sunday
    open_time: str = "00:00"                # HH:MM format
    close_time: str = "23:59"               # HH:MM format
    vercel_toggle: bool = True
    shopee_toggle_last: bool = True
    suspension_status: bool = False         # True = Ya (Penangguhan), False = Tidak
    suspension_reason: str = ""
    suspension_start: str = ""
    suspension_end: str = ""
    subscription_package: str = "Standard"  # e.g., 3 Bulan, 6 Bulan, 12 Bulan
    subscription_start: str = ""
    subscription_end: str = ""
    subscription_total_days: int = 0
    subscription_status: str = "Active"     # Active or Expired
    last_checked_at: str = ""
    raw_extra: Dict[str, Any] = field(default_factory=dict)

    def is_suspended(self) -> bool:
        """Returns True if the merchant outlet is currently suspended by Admin."""
        if isinstance(self.suspension_status, bool):
            return self.suspension_status
        if isinstance(self.suspension_status, str):
            return self.suspension_status.strip().lower() in ["ya", "yes", "true", "1"]
        return False

    def is_subscription_active(self) -> bool:
        """Checks if Auto Open subscription is still valid/active."""
        if self.subscription_status.strip().lower() in ["expired", "nonaktif", "false", "0"]:
            return False

        if self.subscription_end:
            try:
                # Format expected: YYYY-MM-DD
                end_date = datetime.strptime(self.subscription_end.strip()[:10], "%Y-%m-%d")
                if datetime.now() > end_date:
                    return False
            except ValueError:
                pass
        return True

    def is_within_operating_hours(self, now: Optional[datetime] = None) -> bool:
        """Evaluates whether current time falls within configured operational schedule."""
        if now is None:
            now = datetime.now()

        current_weekday = str(now.isoweekday())  # 1=Monday, 7=Sunday
        if self.operating_days and current_weekday not in [d.strip() for d in self.operating_days.split(",")]:
            return False

        try:
            open_h, open_m = map(int, self.open_time.split(":")[:2])
            close_h, close_m = map(int, self.close_time.split(":")[:2])

            current_time = now.time()
            start_t = time(open_h, open_m)
            end_t = time(close_h, close_m)

            if start_t <= end_t:
                return start_t <= current_time <= end_t
            else:  # Overnight schedule (e.g. 18:00 to 02:00)
                return current_time >= start_t or current_time <= end_t
        except Exception as e:
            log.warning(f"Error parsing operating hours for {self.outlet_short_name}: {e}")
            return True

    def calculate_desired_shopee_status(self, now: Optional[datetime] = None) -> tuple[bool, str]:
        """
        Evaluates the 5-level System Priority Hierarchy:
        1. Status Penangguhan (Suspended => Force OFF)
        2. Status Subscription (Expired => Force OFF / Auto Open Disabled)
        3. Vercel Toggle (OFF => Force OFF)
        4. Operating Hours (Outside hours => Force OFF)
        5. Vercel Toggle ON + Active + Operating Hours => Force ON
        Returns (desired_status: bool, reason: str)
        """
        # 1. Status Penangguhan
        if self.is_suspended():
            return False, f"Ditangguhkan Admin ({self.suspension_reason or 'Penangguhan Ya'})"

        # 2. Status Subscription
        if not self.is_subscription_active():
            return False, f"Subscription {self.subscription_status} (Expired)"

        # 3. Vercel Toggle
        if not self.vercel_toggle:
            return False, "Vercel Toggle = OFF"

        # 4. Jam Operasional
        if not self.is_within_operating_hours(now):
            return False, f"Di Luar Jam Operasional ({self.open_time} - {self.close_time})"

        # 5. All criteria met => Auto Open ON
        return True, "Auto Open (Vercel Toggle ON & Dalam Jam Operasional)"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("raw_extra", None)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "OutletData":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_keys}

        # Normalize booleans
        if "vercel_toggle" in filtered:
            val = filtered["vercel_toggle"]
            filtered["vercel_toggle"] = str(val).lower() in ["true", "on", "1", "ya"] if not isinstance(val, bool) else val

        if "shopee_toggle_last" in filtered:
            val = filtered["shopee_toggle_last"]
            filtered["shopee_toggle_last"] = str(val).lower() in ["true", "on", "1", "ya", "open"] if not isinstance(val, bool) else val

        if "suspension_status" in filtered:
            val = filtered["suspension_status"]
            filtered["suspension_status"] = str(val).lower() in ["ya", "yes", "true", "1"] if not isinstance(val, bool) else val

        return cls(**filtered)


class BaseDataProvider(ABC):
    """Abstract interface for all Data Provider implementations."""

    @abstractmethod
    def fetch_all_outlets(self) -> List[OutletData]:
        """Fetches list of all registered outlets."""
        pass

    @abstractmethod
    def update_shopee_status(self, store_id: str, new_status: bool, result_log: str = "") -> bool:
        """Updates the recorded ShopeePartner status for a store."""
        pass

    @abstractmethod
    def update_vercel_toggle(self, store_id: str, new_toggle: bool) -> bool:
        """Updates Vercel Toggle state for a store."""
        pass


class LocalJsonDataProvider(BaseDataProvider):
    """Data provider backed by a local JSON file (data/outlets.json)."""

    def __init__(self, json_file_path: Optional[str] = None):
        if json_file_path is None:
            json_file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data",
                "outlets.json"
            )
        self.file_path = json_file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)
        if not os.path.exists(self.file_path) or os.path.getsize(self.file_path) == 0:
            sample_data = [
                {
                    "store_id": "ST1001",
                    "merchant_id": "M101",
                    "owner_name": "Merchant Foodnesia",
                    "portal_name": "Foodnesia Portal",
                    "outlet_long_name": "Foodnesia Outlet Utama",
                    "outlet_short_name": "Foodnesia",
                    "operating_days": "1,2,3,4,5,6,7",
                    "open_time": "08:00",
                    "close_time": "22:00",
                    "vercel_toggle": True,
                    "shopee_toggle_last": True,
                    "suspension_status": False,
                    "suspension_reason": "",
                    "subscription_package": "6 Bulan",
                    "subscription_start": "2026-01-01",
                    "subscription_end": "2026-12-31",
                    "subscription_status": "Active"
                }
            ]
            with open(self.file_path, "w") as f:
                json.dump(sample_data, f, indent=4)

    def fetch_all_outlets(self) -> List[OutletData]:
        try:
            with open(self.file_path, "r") as f:
                items = json.load(f)
            return [OutletData.from_dict(item) for item in items]
        except Exception as e:
            log.error(f"Error reading JSON data provider ({self.file_path}): {e}")
            return []

    def update_shopee_status(self, store_id: str, new_status: bool, result_log: str = "") -> bool:
        try:
            with open(self.file_path, "r") as f:
                items = json.load(f)

            updated = False
            for item in items:
                if str(item.get("store_id")) == str(store_id):
                    item["shopee_toggle_last"] = new_status
                    item["last_checked_at"] = datetime.now().isoformat()
                    updated = True
                    break

            if updated:
                with open(self.file_path, "w") as f:
                    json.dump(items, f, indent=4)
                return True
            return False
        except Exception as e:
            log.error(f"Failed to update shopee status in JSON provider: {e}")
            return False

    def update_vercel_toggle(self, store_id: str, new_toggle: bool) -> bool:
        try:
            with open(self.file_path, "r") as f:
                items = json.load(f)

            updated = False
            for item in items:
                if str(item.get("store_id")) == str(store_id):
                    item["vercel_toggle"] = new_toggle
                    updated = True
                    break

            if updated:
                with open(self.file_path, "w") as f:
                    json.dump(items, f, indent=4)
                return True
            return False
        except Exception as e:
            log.error(f"Failed to update vercel toggle in JSON provider: {e}")
            return False


class GoogleSheetsDataProvider(BaseDataProvider):
    """
    Data Provider backed by Google Sheets DB.
    Supports CSV export endpoint parsing as well as Service Account / API Key.
    """

    def __init__(self, sheet_id: str, csv_url: Optional[str] = None):
        self.sheet_id = sheet_id
        self.csv_url = csv_url or f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
        self.local_cache_provider = LocalJsonDataProvider()

    def fetch_all_outlets(self) -> List[OutletData]:
        log.info(f"Fetching outlet data from Google Sheets (ID: {self.sheet_id})...")
        try:
            resp = requests.get(self.csv_url, timeout=15)
            if resp.status_code == 200 and "csv" in resp.headers.get("Content-Type", ""):
                import csv
                from io import StringIO

                f = StringIO(resp.text)
                reader = csv.DictReader(f)
                outlets = []
                for row in reader:
                    # Map CSV column headers to OutletData fields
                    d = {
                        "store_id": row.get("Store ID") or row.get("store_id", ""),
                        "merchant_id": row.get("Merchant ID") or row.get("merchant_id", ""),
                        "owner_name": row.get("Nama Pemilik") or row.get("owner_name", ""),
                        "portal_name": row.get("Nama Portal") or row.get("portal_name", ""),
                        "outlet_long_name": row.get("Nama Panjang Outlet") or row.get("outlet_long_name", ""),
                        "outlet_short_name": row.get("Nama Pendek Outlet") or row.get("outlet_short_name", ""),
                        "operating_days": row.get("Hari Operasional") or row.get("operating_days", "1,2,3,4,5,6,7"),
                        "open_time": row.get("Jam Buka") or row.get("open_time", "00:00"),
                        "close_time": row.get("Jam Tutup") or row.get("close_time", "23:59"),
                        "vercel_toggle": row.get("Vercel Toggle", "ON"),
                        "shopee_toggle_last": row.get("Shopee Toggle Terakhir", "ON"),
                        "suspension_status": row.get("Status Penangguhan", "Tidak"),
                        "suspension_reason": row.get("Alasan Penangguhan", ""),
                        "subscription_package": row.get("Paket Subscription", ""),
                        "subscription_start": row.get("Tanggal Mulai Subscription", ""),
                        "subscription_end": row.get("Tanggal Berakhir Subscription", ""),
                        "subscription_status": row.get("Status Subscription", "Active"),
                    }
                    if d["store_id"]:
                        outlets.append(OutletData.from_dict(d))
                log.info(f"Successfully loaded {len(outlets)} outlets from Google Sheets.")
                return outlets
            else:
                log.warning(f"Google Sheets URL returned non-CSV response (Status {resp.status_code}). Falling back to local cache.")
                return self.local_cache_provider.fetch_all_outlets()
        except Exception as e:
            log.error(f"Error accessing Google Sheets ({e}). Falling back to local cache provider.")
            return self.local_cache_provider.fetch_all_outlets()

    def update_shopee_status(self, store_id: str, new_status: bool, result_log: str = "") -> bool:
        return self.local_cache_provider.update_shopee_status(store_id, new_status, result_log)

    def update_vercel_toggle(self, store_id: str, new_toggle: bool) -> bool:
        return self.local_cache_provider.update_vercel_toggle(store_id, new_toggle)


class VercelApiDataProvider(BaseDataProvider):
    """
    Data Provider communicating with Vercel Merchant Dashboard REST API.
    """

    def __init__(self, api_url: str, api_token: Optional[str] = None):
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token or os.environ.get("VERCEL_API_TOKEN", "")
        self.local_cache_provider = LocalJsonDataProvider()

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_token:
            h["Authorization"] = f"Bearer {self.api_token}"
        return h

    def fetch_all_outlets(self) -> List[OutletData]:
        url = f"{self.api_url}/api/outlets"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("outlets", data) if isinstance(data, dict) else data
                return [OutletData.from_dict(item) for item in items]
            log.warning(f"Vercel API returned status code {resp.status_code}. Using local cache fallback.")
            return self.local_cache_provider.fetch_all_outlets()
        except Exception as e:
            log.error(f"Failed to fetch outlets from Vercel API ({url}): {e}. Using local cache fallback.")
            return self.local_cache_provider.fetch_all_outlets()

    def update_shopee_status(self, store_id: str, new_status: bool, result_log: str = "") -> bool:
        url = f"{self.api_url}/api/outlets/{store_id}/shopee-status"
        try:
            resp = requests.post(url, headers=self._headers(), json={
                "shopee_status": new_status,
                "result_log": result_log,
                "timestamp": datetime.now().isoformat()
            }, timeout=10)
            return resp.status_code in [200, 201, 204]
        except Exception as e:
            log.error(f"Failed to update Shopee status via Vercel API: {e}")
            return self.local_cache_provider.update_shopee_status(store_id, new_status, result_log)

    def update_vercel_toggle(self, store_id: str, new_toggle: bool) -> bool:
        url = f"{self.api_url}/api/outlets/{store_id}/vercel-toggle"
        try:
            resp = requests.post(url, headers=self._headers(), json={"vercel_toggle": new_toggle}, timeout=10)
            return resp.status_code in [200, 201, 204]
        except Exception as e:
            log.error(f"Failed to update Vercel toggle via Vercel API: {e}")
            return self.local_cache_provider.update_vercel_toggle(store_id, new_toggle)


class DatabaseDataProvider(BaseDataProvider):
    """Data Provider reading and writing directly to the SQLite Backup database."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def fetch_all_outlets(self) -> List[OutletData]:
        raw_items = self.db.get_outlets_backup()
        return [OutletData.from_dict(item) for item in raw_items]

    def update_shopee_status(self, store_id: str, new_status: bool, result_log: str = "") -> bool:
        outlets = self.fetch_all_outlets()
        for outlet in outlets:
            if outlet.store_id == str(store_id):
                outlet.shopee_toggle_last = new_status
                outlet.last_checked_at = datetime.now().isoformat()
                self.db.save_outlets_backup([outlet.to_dict()])
                return True
        return False

    def update_vercel_toggle(self, store_id: str, new_toggle: bool) -> bool:
        outlets = self.fetch_all_outlets()
        for outlet in outlets:
            if outlet.store_id == str(store_id):
                outlet.vercel_toggle = new_toggle
                self.db.save_outlets_backup([outlet.to_dict()])
                return True
        return False


class HybridDataProvider(BaseDataProvider):
    """
    Hybrid Data Provider:
    Primary: Primary Source of Truth (Google Sheets / Vercel API / Local JSON)
    Backup: SQLite Database (automatically synced on read/write and used as failover)
    """

    def __init__(self, primary_provider: BaseDataProvider, db_manager: Optional[DatabaseManager] = None):
        self.primary = primary_provider
        self.db_manager = db_manager or DatabaseManager()
        self.db_provider = DatabaseDataProvider(self.db_manager)

    def fetch_all_outlets(self) -> List[OutletData]:
        try:
            outlets = self.primary.fetch_all_outlets()
            if outlets:
                # Save snapshot to database backup
                dict_list = [o.to_dict() for o in outlets]
                self.db_manager.save_outlets_backup(dict_list)
                return outlets
        except Exception as e:
            log.error(f"Primary Data Provider failed ({e}). Falling back to SQLite Database backup.")

        # Failover to Database backup
        log.info("Fetching outlets from local SQLite Database backup...")
        return self.db_provider.fetch_all_outlets()

    def update_shopee_status(self, store_id: str, new_status: bool, result_log: str = "") -> bool:
        # Update both primary and database backup
        res_primary = self.primary.update_shopee_status(store_id, new_status, result_log)
        res_db = self.db_provider.update_shopee_status(store_id, new_status, result_log)
        return res_primary or res_db

    def update_vercel_toggle(self, store_id: str, new_toggle: bool) -> bool:
        res_primary = self.primary.update_vercel_toggle(store_id, new_toggle)
        res_db = self.db_provider.update_vercel_toggle(store_id, new_toggle)
        return res_primary or res_db


class DataProviderFactory:
    """Factory to instantiate the appropriate DataProvider based on configuration."""

    @staticmethod
    def create_provider() -> BaseDataProvider:
        provider_type = os.environ.get("DATA_PROVIDER_TYPE", "hybrid").strip().lower()
        sheet_id = os.environ.get("GOOGLE_SHEET_ID", "10osh4rI4q_mv6fBe9NurXRztRrGa85L01Bwned6m0Qs")
        vercel_url = os.environ.get("VERCEL_API_URL", "")

        db_manager = DatabaseManager()

        if provider_type == "sheets":
            primary = GoogleSheetsDataProvider(sheet_id=sheet_id)
        elif provider_type == "vercel" and vercel_url:
            primary = VercelApiDataProvider(api_url=vercel_url)
        elif provider_type == "database":
            return DatabaseDataProvider(db_manager)
        elif provider_type == "local_json":
            return LocalJsonDataProvider()
        else:  # Default to 'hybrid' with Google Sheets primary + SQLite DB backup
            primary = GoogleSheetsDataProvider(sheet_id=sheet_id)

        return HybridDataProvider(primary_provider=primary, db_manager=db_manager)
