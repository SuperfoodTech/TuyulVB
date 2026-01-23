"""
HTTP utility functions for handling compressed responses and JSON parsing.
Consolidates gzip decompression and JSON parsing logic across all scripts.
"""

import gzip
import json
import brotli
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
        encoding = None

        # Determine encoding from headers if available
        if hasattr(response, "headers"):
            content_encoding = response.headers.get("Content-Encoding", "").lower()
            if "gzip" in content_encoding:
                encoding = "gzip"
            elif "br" in content_encoding:
                encoding = "br"
        
        # Override if is_gzipped flag is explicitly set (legacy support)
        if is_gzipped:
            encoding = "gzip"

        # Decompress based on encoding
        if encoding == "gzip":
            body_bytes = gzip.decompress(body_bytes)
        elif encoding == "br":
            body_bytes = brotli.decompress(body_bytes)

        return body_bytes.decode("utf-8")
    except (gzip.BadGzipFile, brotli.error, EOFError) as e:
        log.error(f"Failed to decompress ({encoding}): {e}")
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
