from datetime import datetime


def log(level, message):
    """Prints a message to the console with a timestamp and log level."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level.upper()}] {message}")
