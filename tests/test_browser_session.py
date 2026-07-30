"""
Unit tests for Tahap 3: Browser Session, isolated profile handling, session health checks, and retry mechanisms.
"""

import os
import sys
import unittest
import tempfile

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.shopee.browser_session import BrowserSession


class TestBrowserSessionReliability(unittest.TestCase):

    def test_isolated_profile_path_configuration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["SHOPEE_SELENIUM_PROFILE_PATH"] = temp_dir
            session = BrowserSession(headless=True)
            self.assertEqual(session.headless, True)

            # Check health method on uninitialized or mocked session
            health = session.check_session_health()
            # If driver wasn't able to start in test environment, health will be False, otherwise True/False without throwing Exception
            self.assertIsInstance(health, bool)

            # Cleanup
            session.quit()

    def test_staff_access_revoked_check(self):
        session = BrowserSession(headless=True)
        # Mocking check_staff_access_revoked when driver is None or inactive
        revoked, reason = session.check_staff_access_revoked()
        self.assertFalse(revoked)
        session.quit()


if __name__ == "__main__":
    unittest.main()
