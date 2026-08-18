"""
AUTO-REPLYER
============
The AI that closes deals automatically.

This module:
1. Reads unread replies from Gmail (via IMAP)
2. Detects what the business is asking (intent)
3. Generates the perfect response
4. Sends it automatically
5. Detects when a deal is ready (business says yes/ready to pay)
6. Notifies YOU only when a deal is ready to close

This means businesses get instant replies 24/7, and you only get
notified when money is on the table.

USAGE:
  python3 scripts/auto_replyer.py              (check and reply to all unread)
  python3 scripts/auto_replyer.py --test       (show what would be replied, don't send)
  python3 scripts/auto_replyer.py --once       (run once and exit)
  python3 scripts/auto_replyer.py --watch      (run continuously, check every 5 min)
"""
import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from gmail_reader import read_replies, is_configured as gmail_ok
from email_sender import send_one_email
from reply_handler import detect_intent, RESPONSES
from notifications import send_telegram_notification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data",
                "auto_replyer.log",
            )
        ),
    ],
)
logger = logging.getLogger(__name__)

BUSINESS_NAME = os.getenv("BUSINESS_NAME", "AI Pro Assist")
YOUR_EMAIL = os.getenv("BUSINESS_EMAIL", "")
WHATSAPP_LINK = os.getenv("WHATSAPP_LINK", "")
PAYPAL_EMAIL = os.getenv("PAYPAL_EMAIL", "")
CRYPTO_USDT = os.getenv("CRYPTO_USDT_ADDRESS", "")

# Track which emails we've already replied to (avoid double-replying)
REPLIED_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "auto_replied.json",
)

# Intents that mean a deal is ready (notify the user)
DEAL_READY_INTENTS = ["interested", "yes", "how_much", "demo", "lead_yes", "lead_which", "lead_price"]

# Intents that mean they want to stop (don't pursue)
STOP_INTENTS = ["stop", "not_now"]


def load_replied():
    """Load list of already-replied message IDs."""
    if os.path.exists(REPLIED_FILE):
        with open(REPLIED_FILE) as f:
            return json.load(f)
    return []


def save_replied(replied_list):
    """Save list of replied message IDs."""
    os.makedirs(os.path.dirname(REPLIED_FILE), exist_ok=True)
    with open(REPLIED_FILE, "w") as f:
        json.dump(replied_list, f, indent=2)


def generate_response(intent, business_name=""):
    """Generate the response for a given intent."""
    response = RESPONSES.get(intent, RESPONSES["question"])
    if business_name:
        response = f"Hi {business_name},\n\n" + response
    return response


def extract_business_name_from_email(reply):
    """Try to extract a business name from the sender info."""
    name = reply.get("from_name", "")
    if name:
        # Clean up the name
        name = name.strip().strip('"')
        if len(name) > 2:
            return name
    # Fallback: use email username
    email = reply.get("from_email", "")
    if "@" in email:
        username = email.split("@")[0]
        return username.replace(".", " ").title()
    return "there"


def notify_deal_ready(reply, intent, response_sent):
    """Notify the user that a deal is ready to close."""
    business_name = extract_business_name_from_email(reply)
    message = f"""🔔 NEW DEAL READY!

A business is interested in your AI assistant!

Business: {business_name}
Email: {reply['from_email']}
Intent: {intent}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

What they said:
{reply['body'][:300]}

What the AI replied:
{response_sent[:300]}

👉 NEXT STEP: Check your email and close the deal!
{f'WhatsApp: {WHATSAPP_LINK}' if WHATSAPP_LINK else ''}
"""

    logger.info("🔔 DEAL READY — Notifying user!")
    send_telegram_notification(message)


def process_replies(test_mode=False):
    """Read unread replies, respond automatically, notify on deals."""
    if not gmail_ok():
        logger.error("Gmail not configured. Cannot read replies.")
        return 0, 0

    logger.info("Checking for new replies...")

    replies = read_replies(mark_as_read=True)
    if not replies:
        logger.info("No new replies.")
        return 0, 0

    already_replied = load_replied()
    replied_ids = set(r.get("message_id") for r in already_replied)

    replies_sent = 0
    deals_ready = 0

    for reply in replies:
        msg_id = reply.get("message_id", "")
        if msg_id in replied_ids:
            logger.info(f"Already replied to {reply['from_email']}, skipping")
            continue

        body = reply.get("body", "")
        subject = reply.get("subject", "")
        from_email = reply.get("from_email", "")
        from_name = extract_business_name_from_email(reply)

        # Detect intent from the reply
        intent = detect_intent(body)
        logger.info(f"📨 From: {from_email}")
        logger.info(f"   Subject: {subject[:50]}")
        logger.info(f"   Intent: {intent}")

        # Generate the response
        response = generate_response(intent, from_name)

        if test_mode:
            logger.info(f"   [TEST] Would reply:")
            logger.info(f"   {response[:100]}...")
            replies_sent += 1
        else:
            # Send the reply
            success = send_one_email(from_email, f"Re: {subject.replace('Re: ', '')}", response)
            if success:
                replies_sent += 1
                logger.info(f"   ✅ Replied automatically")

                # Save to replied list
                already_replied.append({
                    "message_id": msg_id,
                    "from_email": from_email,
                    "from_name": from_name,
                    "subject": subject,
                    "body_preview": body[:200],
                    "intent": intent,
                    "response_preview": response[:200],
                    "replied_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                replied_ids.add(msg_id)

                # If deal is ready, notify the user
                if intent in DEAL_READY_INTENTS:
                    deals_ready += 1
                    notify_deal_ready(reply, intent, response)
                elif intent in STOP_INTENTS:
                    logger.info(f"   Business asked to stop — no notification needed")
            else:
                logger.error(f"   ❌ Failed to send reply")

        # Wait between replies
        if not test_mode:
            time.sleep(2)

    save_replied(already_replied)
    logger.info(f"Done! Replied to {replies_sent} emails, {deals_ready} deal(s) ready")
    return replies_sent, deals_ready


def run_once(test_mode=False):
    """Run one check cycle."""
    print("=" * 60)
    print("  🤖 AUTO-REPLYER")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    process_replies(test_mode=test_mode)


def run_watch(interval=300, test_mode=False):
    """Run continuously, checking every N seconds."""
    logger.info(f"Starting auto-replyer in watch mode (checking every {interval}s)")
    logger.info("Press Ctrl+C to stop")

    while True:
        try:
            process_replies(test_mode=test_mode)
        except Exception as e:
            logger.error(f"Error in watch cycle: {e}")

        logger.info(f"Waiting {interval}s until next check...")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Auto-Replyer — AI that closes deals")
    parser.add_argument("--test", action="store_true", help="Show what would be replied, don't send")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--watch", action="store_true", help="Run continuously (check every 5 min)")
    parser.add_argument("--interval", type=int, default=300, help="Watch interval in seconds (default 300)")
    args = parser.parse_args()

    if args.watch:
        run_watch(interval=args.interval, test_mode=args.test)
    else:
        run_once(test_mode=args.test)


if __name__ == "__main__":
    main()
