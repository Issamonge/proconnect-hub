#!/usr/bin/env python3
"""
Send outreach emails to extracted leads that haven't been contacted yet.
Uses the same high-converting email templates from better_emails.py.
"""
import os
import sys
import json
import smtplib
import time
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from better_emails import generate_better_email, NICHE_ANGLES

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
EXTRACTED_FILE = os.path.join(DATA_DIR, "extracted_emails.json")
SENT_FILE = os.path.join(DATA_DIR, "sent_emails.json")
SCAN_FILE = os.path.join(DATA_DIR, "scan_results.json")

GMAIL_EMAIL = os.getenv("BUSINESS_EMAIL", "ihakizimana11@gmail.com")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "AI Pro Assist")
WHATSAPP_LINK = os.getenv("WHATSAPP_LINK", "https://wa.me/971505852438")

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def send_email(to_email, subject, body):
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

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50, help="Max emails to send")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be sent without sending")
    args = parser.parse_args()

    extracted = load_json(EXTRACTED_FILE)
    sent = load_json(SENT_FILE)
    leads = load_json(SCAN_FILE)

    # Build lookup from leads by website
    leads_by_website = {}
    for l in leads:
        w = l.get("website", "").lower().rstrip("/")
        if w:
            leads_by_website[w] = l

    sent_emails = set(s.get("to", "").lower() for s in sent)

    # Find emails to send
    to_send = []
    for e in extracted:
        email = e.get("email", "")
        if not email or email.lower() in sent_emails:
            continue
        # Find matching lead for niche info
        website = e.get("website", "").lower().rstrip("/")
        lead = leads_by_website.get(website, e)
        to_send.append({
            "email": email,
            "name": e.get("name", ""),
            "niche": e.get("niche", lead.get("scan_niche", lead.get("niche", ""))),
            "city": e.get("city", lead.get("scan_city", "")),
            "website": e.get("website", ""),
        })

    logger.info(f"Found {len(to_send)} emails to send (limit: {args.limit})")

    if args.dry_run:
        for t in to_send[:args.limit]:
            angle = NICHE_ANGLES.get(t["niche"], NICHE_ANGLES["plumber"])
            logger.info(f"  → {t['email']} ({t['niche']}, {t['city']}) — Subject: {angle['subject']}")
        return

    sent_count = 0
    for t in to_send[:args.limit]:
        # Create a lead-like dict for generate_better_email
        lead_dict = {
            "name": t["name"],
            "scan_niche": t["niche"],
            "scan_city": t["city"],
            "website": t["website"],
        }
        email_data = generate_better_email(lead_dict)

        if send_email(t["email"], email_data["subject"], email_data["body"]):
            sent.append({
                "to": t["email"],
                "name": t["name"],
                "niche": t["niche"],
                "city": t["city"],
                "subject": email_data["subject"],
                "sent_at": datetime.now().isoformat(),
                "status": "sent",
            })
            sent_emails.add(t["email"].lower())
            sent_count += 1
            logger.info(f"  ✅ Sent to {t['email']} ({t['niche']}, {t['city']})")
            time.sleep(5)  # Rate limit: 5 seconds between emails
        else:
            logger.error(f"  ❌ Failed: {t['email']}")

    save_json(SENT_FILE, sent)
    logger.info(f"DONE! Sent {sent_count} emails. Total sent: {len(sent)}")

if __name__ == "__main__":
    main()
