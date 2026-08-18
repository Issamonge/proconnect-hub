#!/usr/bin/env python3
"""
FOLLOW-UP EMAIL SENDER
======================
Sends follow-up emails to leads who didn't respond to the first email.
Includes PayPal payment link to make it easy to pay.

Follow-up sequence:
  - Follow-up 1: 3 days after original email ("Just checking in")
  - Follow-up 2: 7 days after original email ("Last email + special offer")

Usage:
  python3 scripts/follow_up_sender.py            # send follow-ups due now
  python3 scripts/follow_up_sender.py --check    # see what's due (don't send)
"""
import os
import sys
import json
import smtplib
import logging
import argparse
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SENT_FILE = os.path.join(DATA_DIR, "sent_emails.json")
FOLLOWUP_FILE = os.path.join(DATA_DIR, "follow_ups_sent.json")

GMAIL_EMAIL = os.getenv("BUSINESS_EMAIL", "ihakizimana11@gmail.com")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "AI Pro Assist")
WHATSAPP_LINK = os.getenv("WHATSAPP_LINK", "https://wa.me/971505852438")
BUSINESS_PHONE = os.getenv("BUSINESS_PHONE", "+971502584233")
PAYPAL_EMAIL = os.getenv("PAYPAL_EMAIL", "ihakizimana11@gmail.com")
LANDING_PAGE_URL = os.getenv("LANDING_PAGE_URL", "")

# PayPal payment link (paypal.me/username)
PAYPAL_LINK = f"https://www.paypal.com/paypalme/{PAYPAL_EMAIL.split('@')[0]}/500"
PAYPAL_MONTHLY_LINK = f"https://www.paypal.com/paypalme/{PAYPAL_EMAIL.split('@')[0]}/200"

# Crypto wallet for alternative payment
CRYPTO_WALLET = os.getenv("CRYPTO_WALLET", "0x27e16d0df86a051e1b14c0f5b90db76d74fd0704")


def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def send_email(to_email, subject, body):
    """Send email via Gmail SMTP."""
    msg = MIMEMultipart()
    msg["From"] = f"{BUSINESS_NAME} <{GMAIL_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_EMAIL, GMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send to {to_email}: {e}")
        return False


def follow_up_1_email(business_name, niche):
    """Follow-up 1: sent 3 days after original email."""
    subject = "Re: following up on my last email"

    body = f"""Hi {business_name},

I sent you an email a few days ago about an AI voice assistant that answers your phone 24/7.

I know you're busy, so I'll keep this short:

Your customers are calling when you can't answer. Each missed call is a lost job worth $200-$2,000+.

My AI assistant:
  ✅ Answers every call, 24/7
  ✅ Books appointments into your calendar
  ✅ Sends you a text with every lead
  ✅ Never takes a sick day, never sleeps

Setup: $500 one-time
Monthly: $200 (all calls included)

Ready to stop losing customers to voicemail?

Reply "YES" and I'll set you up this week.

Or pay now and we'll start immediately:
  One-time setup ($500): {PAYPAL_LINK}

You can also reach me:
  📱 WhatsApp: {WHATSAPP_LINK}
  📞 Phone: {BUSINESS_PHONE}

Best,
{BUSINESS_NAME}

---
Reply "UNSUBSCRIBE" to stop receiving emails.
"""
    return subject, body


def follow_up_2_email(business_name, niche):
    """Follow-up 2: sent 7 days after original email (last email + special offer)."""
    subject = "Last email — special offer inside"

    body = f"""Hi {business_name},

This is my last email, but I want to make you a special offer.

I know trying new technology feels risky. So here's my deal:

  💰 First month FREE — no charge for 30 days
  💰 Setup fee waived (save $500)
  💰 If you don't get at least 3 new customers from it, you pay nothing

You only start paying $200/month AFTER the free month, and only if it's bringing you business.

No risk. No contract. Cancel anytime.

To claim this offer, just reply "FREE" to this email.

Or book directly:
  PayPal (start after free month): {PAYPAL_MONTHLY_LINK}
  WhatsApp me: {WHATSAPP_LINK}
  Call me: {BUSINESS_PHONE}

This offer is only for the first 10 businesses that respond.

Best,
{BUSINESS_NAME}

---
Reply "UNSUBSCRIBE" to stop receiving emails.
"""
    return subject, body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Show what's due without sending")
    args = parser.parse_args()

    sent = load_json(SENT_FILE)
    followups = load_json(FOLLOWUP_FILE)

    # Track which follow-ups have been sent
    sent_keys = set()
    for f in followups:
        sent_keys.add((f.get("to"), f.get("followup_num")))

    now = datetime.now()
    due_followups = []

    for s in sent:
        sent_date_str = s.get("sent_at", "")
        if not sent_date_str:
            continue
        try:
            sent_date = datetime.fromisoformat(sent_date_str.replace("Z", ""))
        except:
            continue

        to_email = s.get("to", "")
        niche = s.get("niche", "")
        business_name = s.get("business_name", s.get("to", "").split("@")[0])

        days_since = (now - sent_date).days

        # Follow-up 1: due after 3 days
        if days_since >= 3 and (to_email, 1) not in sent_keys:
            due_followups.append({
                "to": to_email,
                "niche": niche,
                "business_name": business_name,
                "followup_num": 1,
                "days_since": days_since,
            })

        # Follow-up 2: due after 7 days
        if days_since >= 7 and (to_email, 2) not in sent_keys:
            due_followups.append({
                "to": to_email,
                "niche": niche,
                "business_name": business_name,
                "followup_num": 2,
                "days_since": days_since,
            })

    logger.info(f"Found {len(due_followups)} follow-ups due")

    if args.check:
        for d in due_followups:
            logger.info(f"  Follow-up #{d['followup_num']} → {d['to']} ({d['niche']}) — {d['days_since']} days since original")
        return

    sent_count = 0
    for d in due_followups:
        if d["followup_num"] == 1:
            subject, body = follow_up_1_email(d["business_name"], d["niche"])
        else:
            subject, body = follow_up_2_email(d["business_name"], d["niche"])

        if send_email(d["to"], subject, body):
            followups.append({
                "to": d["to"],
                "niche": d["niche"],
                "business_name": d["business_name"],
                "followup_num": d["followup_num"],
                "subject": subject,
                "sent_at": now.isoformat(),
                "status": "sent",
            })
            sent_count += 1
            logger.info(f"  ✅ Follow-up #{d['followup_num']} sent to {d['to']}")
            import time
            time.sleep(3)  # Rate limit
        else:
            logger.error(f"  ❌ Failed to send follow-up to {d['to']}")

    save_json(FOLLOWUP_FILE, followups)
    logger.info(f"Done! Sent {sent_count} follow-up emails")


if __name__ == "__main__":
    main()
