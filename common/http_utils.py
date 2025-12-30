"""
HTTP utility functions for handling compressed responses and JSON parsing.
Consolidates gzip decompression and JSON parsing logic across all scripts.
"""

import gzip
import json
from common.logger import get_logger

log = get_logger("http_utils")


def decompress_response_body(response, is_gzipped=None):
    """
    Safely decompresses and decodes HTTP response body.

    Args:
        response: Selenium request response object or raw bytes
        is_gzipped: If True, force gzip decompression. If None, check headers.

    Returns:
        Decoded string or None if decompression fails
    """
    try:
        body_bytes = response.body if hasattr(response, "body") else response

        # Determine if gzipped
        if is_gzipped is None and hasattr(response, "headers"):
            is_gzipped = response.headers.get("Content-Encoding") == "gzip"
        else:
            is_gzipped = is_gzipped or False

        # Decompress if needed
        if is_gzipped:
            body_bytes = gzip.decompress(body_bytes)

        return body_bytes.decode("utf-8")
    except (gzip.BadGzipFile, EOFError) as e:
        log.error(f"Failed to decompress gzip: {e}")
        return None
    except UnicodeDecodeError as e:
        log.error(f"Failed to decode response: {e}")
        return None


def parse_response_json(response, is_gzipped=None):
    """
    Safely decompresses and parses JSON from response.

    Args:
        response: Selenium request response object or raw bytes
        is_gzipped: If True, force gzip decompression. If None, check headers.

    Returns:
        Parsed dict/list or None if parsing fails
    """
    response_text = decompress_response_body(response, is_gzipped)
    if not response_text:
        return None

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse JSON: {e}")
        return None
