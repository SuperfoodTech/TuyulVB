"""Service factory for singleton access to service clients.

Initial lightweight implementation used for refactoring scaffolding.
"""
from typing import Dict
from .config_manager import ServiceConfig
from services.monday.client import MondayClient
from services.web_scraping.grab_scraper import GrabScraper


class ServiceFactory:
    """Manages the creation and retrieval of service instances."""
    _instances: Dict[str, object] = {}
    _config: ServiceConfig = None

    @classmethod
    def _get_config(cls) -> ServiceConfig:
        if cls._config is None:
            cls._config = ServiceConfig.from_env()
            cls._config.validate()
        return cls._config

    @classmethod
    def get_monday_client(cls):
        if 'monday' not in cls._instances:
            config = cls._get_config()
            cls._instances['monday'] = MondayClient(
                api_key=config.monday_api_key)
        return cls._instances['monday']

    @classmethod
    def get_grab_scraper(cls):
        if 'grab_scraper' not in cls._instances:
            config = cls._get_config()
            cls._instances['grab_scraper'] = GrabScraper(
                credentials=config.grab_credentials)
        return cls._instances['grab_scraper']

    @classmethod
    def shutdown_services(cls):
        """Gracefully shuts down stateful services like web scrapers."""
        if 'grab_scraper' in cls._instances:
            cls._instances['grab_scraper'].quit()
            del cls._instances['grab_scraper']
        return cls._instances['grab_scraper']

    @classmethod
    def get_shopee_scraper(cls):
        if 'shopee_scraper' not in cls._instances:
            from services.web_scraping.shopee_scraper import ShopeeScraper
            config = cls._get_config()
            cls._instances['shopee_scraper'] = ShopeeScraper(
                credentials=config.shopee_credentials)
        return cls._instances['shopee_scraper']
