"""
Unit tests for Tahap 5: REST API Server Bridge & Web Dashboard Endpoints.
"""

import os
import sys
import json
import unittest
import threading
import time
import requests

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api_server import run_api_server, API_SECRET_KEY


class TestApiServerEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_port = 18899
        cls.base_url = f"http://127.0.0.1:{cls.test_port}"
        cls.headers = {"X-API-Key": API_SECRET_KEY}

        # Start API server in background thread
        cls.server_thread = threading.Thread(
            target=run_api_server, kwargs={"port": cls.test_port}, daemon=True
        )
        cls.server_thread.start()
        time.sleep(1)  # Allow server to initialize

    def test_01_health_check_endpoint(self):
        resp = requests.get(f"{self.base_url}/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")

    def test_02_unauthorized_access(self):
        resp = requests.get(f"{self.base_url}/api/outlets")  # Missing X-API-Key
        self.assertEqual(resp.status_code, 401)

    def test_03_get_outlets_endpoint(self):
        resp = requests.get(f"{self.base_url}/api/outlets", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        if data:
            self.assertIn("store_id", data[0])
            self.assertIn("desired_status", data[0])

    def test_04_get_sessions_endpoint(self):
        resp = requests.get(f"{self.base_url}/api/sessions", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)

    def test_05_get_logs_endpoint(self):
        resp = requests.get(f"{self.base_url}/api/logs", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)

    def test_06_post_toggle_endpoint(self):
        payload = {"store_id": "ST1001", "vercel_toggle": True}
        resp = requests.post(
            f"{self.base_url}/api/toggle", headers=self.headers, json=payload
        )
        self.assertIn(resp.status_code, [200, 404])


if __name__ == "__main__":
    unittest.main()
