"""Simple logging wrapper to standardize log format across services."""
import logging


def setup_logging(level: str = 'INFO'):
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    return logging.getLogger('sf_automation')
