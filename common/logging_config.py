"""
Centralized logging configuration for the entire automation suite.
All modules should use get_logger() from common.logger instead of configuring
logging directly, to ensure consistent formatting and propagation handling.

This module provides the configuration that get_logger() uses.
"""

import logging
import sys
import os
import warnings

# Standard log format used across all modules
LOG_FORMAT = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Default log level
DEFAULT_LOG_LEVEL = logging.INFO


def configure_logging(level=DEFAULT_LOG_LEVEL):
    """
    Configures the root logger with standard format.
    Called automatically when modules use get_logger().

    Args:
        level: Logging level (default: INFO)
    """
    root_logger = logging.getLogger()

    # Apply a narrow warnings filter to suppress the known deprecation
    # about datetime.utcnow() that appears repeatedly in runtime output.
    try:
        warnings.filterwarnings(
            "ignore",
            message=r".*datetime\.datetime\.utcnow.*",
            category=DeprecationWarning,
        )
    except Exception:
        # if warnings module behaves unexpectedly, continue without failing
        pass

    # Only configure if not already configured
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        # Allow override via environment variable; fall back to provided level
        env_level = os.environ.get("SF_LOG_LEVEL")
        if env_level:
            try:
                root_logger.setLevel(getattr(logging, env_level.upper()))
            except Exception:
                root_logger.setLevel(level)
        else:
            root_logger.setLevel(level)

    # Quiet noisy external libraries commonly used by Selenium/Chrome
    for noisy in (
        "selenium",
        "urllib3",
        "googleapiclient",
        "google_apis",
        "selenium.webdriver.remote",
        "http.client",
    ):
        try:
            logging.getLogger(noisy).setLevel(logging.WARNING)
        except Exception:
            pass


def get_log_config():
    """
    Returns the standard logging configuration.

    Returns:
        Dict with 'format' and 'datefmt' keys for logging.basicConfig()
    """
    return {"format": LOG_FORMAT, "datefmt": DATE_FORMAT, "level": DEFAULT_LOG_LEVEL}
