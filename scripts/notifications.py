"""
NOTIFICATIONS
=============
Sends notifications to you when leads come in or deals close.
Currently supports Telegram (free, easy). Can be extended to email, etc.
"""
import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

NOTIFICATION_TELEGRAM_TOKEN = os.getenv("NOTIFICATION_TELEGRAM_BOT_TOKEN", "")
NOTIFICATION_TELEGRAM_CHAT_ID = os.getenv("NOTIFICATION_TELEGRAM_CHAT_ID", "")


def send_telegram_notification(message):
    """Send a notification to the user via Telegram."""
    if not NOTIFICATION_TELEGRAM_TOKEN or not NOTIFICATION_TELEGRAM_CHAT_ID:
        logger.info("Telegram not configured - skipping notification")
        return False
    url = f"https://api.telegram.org/bot{NOTIFICATION_TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": NOTIFICATION_TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        requests.post(url, json=payload, timeout=10)
        logger.info("Telegram notification sent")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False


if __name__ == "__main__":
    print("Notifications module")
    print(f"Telegram configured: {bool(NOTIFICATION_TELEGRAM_TOKEN)}")
