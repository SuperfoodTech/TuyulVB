"""Simple configuration manager to load service config from environment.
"""
import os
from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class ServiceConfig:
    monday_api_key: Optional[str]
    google_creds_file: Optional[str]
    google_sheet_name: Optional[str]
    grab_credentials: Dict[str, Dict[str, str]] = field(default_factory=dict)
    shopee_credentials: Dict[str, Dict[str, str]] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> 'ServiceConfig':
        config = cls(
            monday_api_key=os.getenv('MONDAY_API_KEY'),
            google_creds_file=os.getenv('GOOGLE_CREDS_FILE'),
            google_sheet_name=os.getenv('GOOGLE_SHEET_NAME')
        )
        config.load_grab_credentials()
        config.load_shopee_credentials()
        return config

    def load_grab_credentials(self):
        """Loads Grab credentials from environment variables."""
        portals = ["F1", "F2", "F2S", "W1", "L1", "L2", "DE1", "DE1S"]
        for portal in portals:
            username = os.getenv(f'GRAB_USERNAME_{portal}')
            password = os.getenv(f'GRAB_PASSWORD_{portal}')
            if username and password:
                self.grab_credentials[portal] = {
                    "username": username,
                    "password": password
                }

    def load_shopee_credentials(self):
        """Loads Shopee credentials from environment variables."""
        portals = ["ALLVBADMIN", "F", "W", "L"]
        for portal in portals:
            username = os.getenv(f'SHOPEE_USERNAME_{portal.upper()}')
            password = os.getenv(f'SHOPEE_PASSWORD_{portal.upper()}')
            if username and password:
                self.shopee_credentials[portal] = {
                    "username": username,
                    "password": password
                }

    def validate(self) -> bool:
        required = ['monday_api_key', 'google_creds_file']
        missing = [f for f in required if not getattr(self, f)]
        if missing:
            raise ValueError(f"Missing required configuration: {missing}")
        return True
