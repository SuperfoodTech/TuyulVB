"""
Centralized environment configuration and validation.
All scripts should use this module to load and validate configuration
instead of directly calling os.getenv() and checking values.

This ensures consistent validation and error handling across the codebase.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables once at module import
load_dotenv()

# Configure logging for this module
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("config")


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""

    pass


class EnvConfig:
    """
    Centralized environment configuration with validation.

    Usage:
        config = EnvConfig()
        config.validate()  # Raises ConfigurationError if invalid
        api_key = config.MONDAY_API_KEY
        webhook_url = config.DISCORD_WEBHOOK_URL
    """

    # Core API credentials
    MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

    # Optional configurations
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

    @classmethod
    def validate(cls):
        """
        Validates that all required configuration is present and valid.

        Raises:
            ConfigurationError: If required config is missing or invalid
        """
        errors = []

        # Check required environment variables
        if not cls.MONDAY_API_KEY:
            errors.append("MONDAY_API_KEY is required but not set in .env")

        if not cls.DISCORD_WEBHOOK_URL:
            errors.append("DISCORD_WEBHOOK_URL is required but not set in .env")

        # Validate API key format (should have minimum length)
        if cls.MONDAY_API_KEY and len(cls.MONDAY_API_KEY) < 20:
            errors.append(
                f"MONDAY_API_KEY appears invalid (too short: {len(cls.MONDAY_API_KEY)} chars)"
            )

        # Validate webhook URL format
        if cls.DISCORD_WEBHOOK_URL and not cls.DISCORD_WEBHOOK_URL.startswith(
            "https://"
        ):
            errors.append("DISCORD_WEBHOOK_URL must be a valid HTTPS URL")

        # Validate LOG_LEVEL
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if cls.LOG_LEVEL not in valid_levels:
            errors.append(
                f"LOG_LEVEL must be one of {valid_levels}, got: {cls.LOG_LEVEL}"
            )

        # Validate POLL_INTERVAL_SECONDS
        if cls.POLL_INTERVAL_SECONDS <= 0:
            errors.append(
                f"POLL_INTERVAL_SECONDS must be positive, got: {cls.POLL_INTERVAL_SECONDS}"
            )

        if errors:
            error_message = "\n".join(f"  ❌ {error}" for error in errors)
            raise ConfigurationError(
                f"Configuration validation failed:\n{error_message}"
            )

        log.info("✅ Configuration validation passed")

    @classmethod
    def get_monday_api_key(cls) -> str:
        """Safely gets Monday API key with fallback."""
        if not cls.MONDAY_API_KEY:
            raise ConfigurationError("MONDAY_API_KEY not configured")
        return cls.MONDAY_API_KEY

    @classmethod
    def get_discord_webhook_url(cls) -> str:
        """Safely gets Discord webhook URL with fallback."""
        if not cls.DISCORD_WEBHOOK_URL:
            raise ConfigurationError("DISCORD_WEBHOOK_URL not configured")
        return cls.DISCORD_WEBHOOK_URL

    @classmethod
    def to_dict(cls) -> dict:
        """Converts configuration to dictionary for inspection."""
        return {
            "MONDAY_API_KEY": "***REDACTED***" if cls.MONDAY_API_KEY else None,
            "DISCORD_WEBHOOK_URL": (
                "***REDACTED***" if cls.DISCORD_WEBHOOK_URL else None
            ),
            "LOG_LEVEL": cls.LOG_LEVEL,
            "POLL_INTERVAL_SECONDS": cls.POLL_INTERVAL_SECONDS,
        }


def get_config() -> EnvConfig:
    """
    Returns the centralized configuration object.

    Returns:
        EnvConfig instance with all environment variables loaded
    """
    return EnvConfig()
