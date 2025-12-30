import logging
import requests
from datetime import datetime


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