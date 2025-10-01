import socket
from datetime import datetime


def log(level, message):
    """Prints a message to the console with a timestamp and log level."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level.upper()}] {message}")


def is_network_available():
    """Checks for an active internet connection."""
    try:
        # Connect to a reliable, fast DNS server
        socket.create_connection(("1.1.1.1", 53), timeout=5)
        return True
    except OSError:
        return False
