"""
REST API Server Bridge for FoodMaster Auto Open & Auto Close Bot
Compatible with Web Dashboard (/home/asya/Downloads/get menu outlet/web/)
Port: 18800 (default)
Auth Header: X-API-Key: foodmaster-secret-api-key-2026
"""

import os
import sys
import json
import time
import threading
from typing import Any, Dict, List, Optional
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.logger import get_logger
from common.data_provider import DataProviderFactory, OutletData
from common.db_manager import DatabaseManager
from modules.shopee.force_open.refactored import run_force_open

log = get_logger("api_server")

API_PORT = int(os.environ.get("API_PORT", 18800))
API_SECRET_KEY = os.environ.get("API_SECRET_KEY", "foodmaster-secret-api-key-2026")


class RequestHandler(BaseHTTPRequestHandler):

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def _authenticate(self) -> bool:
        if not API_SECRET_KEY:
            return True  # Auth disabled if empty key

        client_key = self.headers.get("X-API-Key") or self.headers.get("x-api-key")
        if client_key and client_key.strip() == API_SECRET_KEY.strip():
            return True

        self.send_response(401)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Unauthorized. Invalid X-API-Key"}).encode("utf-8"))
        return False

    def _respond_json(self, status_code: int, data: Any):
        self.send_response(status_code)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/")

        if path == "/api/health" or path == "/health":
            return self._respond_json(200, {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "service": "FoodMaster Bot API Server"
            })

        if not self._authenticate():
            return

        if path == "/api/outlets":
            try:
                provider = DataProviderFactory.create_provider()
                outlets = provider.fetch_all_outlets()
                result = []
                for o in outlets:
                    item = o.to_dict()
                    desired_status, reason = o.calculate_desired_shopee_status()
                    item["desired_status"] = "OPEN" if desired_status else "OFF"
                    item["priority_reason"] = reason
                    result.append(item)
                return self._respond_json(200, result)
            except Exception as e:
                log.error(f"API Error fetching outlets: {e}")
                return self._respond_json(500, {"error": str(e)})

        elif path == "/api/sessions":
            try:
                profile_path = os.environ.get(
                    "SHOPEE_SELENIUM_PROFILE_PATH",
                    os.path.join(PROJECT_ROOT, "chromeprofile")
                )
                has_session = os.path.exists(profile_path) and len(os.listdir(profile_path)) > 0

                provider = DataProviderFactory.create_provider()
                outlets = provider.fetch_all_outlets()

                sessions_data = []
                for o in outlets:
                    sessions_data.append({
                        "store_id": o.store_id,
                        "merchant_name": o.portal_name or o.outlet_long_name,
                        "nama_resto_final": o.outlet_long_name,
                        "nama_outlet": o.outlet_short_name,
                        "platform": "shopee",
                        "has_session": has_session,
                        "phone": o.merchant_id,
                        "last_login": o.last_checked_at or datetime.now().isoformat()
                    })
                return self._respond_json(200, sessions_data)
            except Exception as e:
                log.error(f"API Error fetching sessions: {e}")
                return self._respond_json(500, {"error": str(e)})

        elif path == "/api/logs" or path == "/api/audit-logs":
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM bot_logs ORDER BY id DESC LIMIT 50")
                    rows = cursor.fetchall()
                    logs = [dict(row) for row in rows]
                return self._respond_json(200, logs)
            except Exception as e:
                log.error(f"API Error fetching audit logs: {e}")
                return self._respond_json(500, {"error": str(e)})

        self._respond_json(404, {"error": f"Endpoint GET {self.path} not found"})

    def do_POST(self):
        if not self._authenticate():
            return

        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/")

        content_length = int(self.headers.get("Content-Length", 0))
        body_str = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            body = json.loads(body_str) if body_str else {}
        except json.JSONDecodeError:
            body = {}

        if path == "/api/toggle":
            store_id = str(body.get("store_id", ""))
            new_toggle = bool(body.get("vercel_toggle", True))
            if not store_id:
                return self._respond_json(400, {"error": "Missing 'store_id' parameter"})

            try:
                provider = DataProviderFactory.create_provider()
                success = provider.update_vercel_toggle(store_id, new_toggle)
                # Safely trigger background cycle
                threading.Thread(
                    target=run_force_open,
                    kwargs={"data_provider": provider, "dry_run": True},
                    daemon=True
                ).start()
                return self._respond_json(200, {
                    "status": "success",
                    "store_id": store_id,
                    "vercel_toggle": new_toggle,
                    "message": "Vercel toggle updated and store sync triggered."
                })
            except Exception as e:
                log.error(f"Error processing /api/toggle: {e}")
                return self._respond_json(500, {"error": str(e)})

        elif path == "/api/trigger-sync":
            try:
                dry_run = bool(body.get("dry_run", True))
                provider = DataProviderFactory.create_provider()
                stats = run_force_open(data_provider=provider, dry_run=dry_run)
                return self._respond_json(200, {
                    "status": "completed",
                    "timestamp": datetime.now().isoformat(),
                    "stats": stats
                })
            except Exception as e:
                log.error(f"Error processing /api/trigger-sync: {e}")
                return self._respond_json(500, {"error": str(e)})

        self._respond_json(404, {"error": f"Endpoint POST {self.path} not found"})


def run_api_server(port: int = API_PORT):
    """Starts the REST API HTTP server."""
    server_address = ("", port)
    httpd = HTTPServer(server_address, RequestHandler)
    log.info(f"🌐 REST API Server running on port {port} (X-API-Key: {API_SECRET_KEY})...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("API Server stopped by user.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_api_server()
