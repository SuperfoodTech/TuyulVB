"""
Centralized logging configuration for the entire automation suite.
All modules should use get_logger() from common.logger instead of configuring
logging directly, to ensure consistent formatting and propagation handling.

This module provides the configuration that get_logger() uses.
"""

import logging
import sys

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

    # Only configure if not already configured
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        root_logger.setLevel(level)


def get_log_config():
    """
    Returns the standard logging configuration.

    Returns:
        Dict with 'format' and 'datefmt' keys for logging.basicConfig()
    """
    return {"format": LOG_FORMAT, "datefmt": DATE_FORMAT, "level": DEFAULT_LOG_LEVEL}
