import logging
import requests
from datetime import datetime
import os


def send_discord_notification(webhook_url: str, title: str, description: str, fields: list = None, color: int = 3066993):
    """
    Sends a standardized, embedded notification to a Discord webhook.

    Args:
        webhook_url (str): The Discord webhook URL.
        title (str): The title of the embed.
        description (str): The main content of the embed.
        fields (list, optional): A list of field objects for the embed. Defaults to None.
        color (int, optional): The color of the embed's side bar. Defaults to green.
    """
    if not webhook_url:
        logging.info("Discord webhook URL not configured. Skipping notification.")
        return

    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.utcnow().isoformat(),
        "fields": fields or []
    }

    try:
        response = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
        response.raise_for_status()
        logging.info("Successfully sent Discord notification.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send Discord notification: {e}")


def send_discord_file(webhook_url: str, file_path: str, content: str = None):
    """
    Sends a file to a Discord webhook.

    Args:
        webhook_url (str): The Discord webhook URL.
        file_path (str): The path to the file to send.
        content (str, optional): A message to accompany the file.
    """
    if not webhook_url:
        logging.info("Discord webhook URL not configured. Skipping file upload.")
        return

    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}. Cannot send to Discord.")
        return

    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            data = {"content": content} if content else {}
            response = requests.post(webhook_url, data=data, files=files, timeout=60)
            response.raise_for_status()
        logging.info(f"Successfully sent file to Discord: {file_path}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send file to Discord: {e}")
