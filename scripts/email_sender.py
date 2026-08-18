"""
EMAIL SENDER (Gmail SMTP)
=========================
Sends outreach emails automatically using Gmail's free SMTP.

FREE: Gmail allows 500 emails/day via SMTP.

SETUP (one-time, you do this):
  1. You need a Gmail account (you have ihakizimana11@gmail.com)
  2. Enable 2-Factor Authentication on your Google account
  3. Generate an "App Password" for this tool:
     - Go to https://myaccount.google.com/apppasswords
     - Create a password for "Mail"
     - Put it in your .env as GMAIL_APP_PASSWORD

USAGE:
  python3 scripts/email_sender.py --dry-run     (show what would be sent, don't send)
  python3 scripts/email_sender.py --limit 10    (send 10 emails)
  python3 scripts/email_sender.py               (send to all leads with emails)
  python3 scripts/email_sender.py --niche plumber  (plumbers only)

LEGAL (CAN-SPAM Act compliance):
  - Includes your real email (sender)
  - Includes unsubscribe option
  - No deceptive subject lines
"""
import os
import sys
import json
import time
import smtplib
import logging
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from better_emails import generate_better_email, clean_name
from email_extractor import get_leads_with_emails

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

GMAIL_USER = os.getenv("GMAIL_USER", os.getenv("BUSINESS_EMAIL", ""))
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "AI Pro Assist")

# Track sent emails to avoid duplicates
SENT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "sent_emails.json",
)


def is_configured():
    """Check if Gmail SMTP is configured."""
    return bool(GMAIL_USER and GMAIL_APP_PASSWORD)


def load_sent():
    """Load list of already-sent emails."""
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE) as f:
            return json.load(f)
    return []


def save_sent(sent_list):
    """Save list of sent emails."""
    os.makedirs(os.path.dirname(SENT_FILE), exist_ok=True)
    with open(SENT_FILE, "w") as f:
        json.dump(sent_list, f, indent=2)


def send_one_email(to_email, subject, body, dry_run=False):
    """Send a single email via Gmail SMTP."""
    if dry_run:
        logger.info(f"  [DRY RUN] Would send to: {to_email}")
        logger.info(f"  [DRY RUN] Subject: {subject}")
        return True

    msg = MIMEMultipart()
    msg["From"] = f"{BUSINESS_NAME} <{GMAIL_USER}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"  Failed to send to {to_email}: {e}")
        return False


def send_outreach(limit=None, dry_run=False, niche=None):
    """Send outreach emails to all leads with extracted emails."""
    if not dry_run and not is_configured():
        logger.error("Gmail not configured!")
        logger.error("Set these in your .env file:")
        logger.error("  GMAIL_USER=your@gmail.com")
        logger.error("  GMAIL_APP_PASSWORD=your_app_password")
        logger.error("")
        logger.error("To get an App Password:")
        logger.error("  1. Go to https://myaccount.google.com/apppasswords")
        logger.error("  2. Enable 2FA first if not already")
        logger.error("  3. Create a password for 'Mail'")
        return 0

    leads = get_leads_with_emails()
    if not leads:
        logger.error("No leads with emails. Run email_extractor.py first!")
        return 0

    if niche:
        leads = [l for l in leads if l.get("niche") == niche]
    if limit:
        leads = leads[:limit]

    already_sent = load_sent()
    sent_emails_set = set(s.get("to") for s in already_sent)

    logger.info(f"Ready to email {len(leads)} leads")
    if dry_run:
        logger.info("DRY RUN - no emails will be sent")

    sent_count = 0
    for i, lead in enumerate(leads, 1):
        emails = lead.get("emails", [])
        if not emails:
            continue

        to_email = emails[0]  # Use the best email found

        # Skip if already sent
        if to_email in sent_emails_set:
            logger.info(f"[{i}/{len(leads)}] Already sent to {to_email}, skipping")
            continue

        # Generate the email
        name = clean_name(lead.get("name", ""))
        # Build a lead dict for the email generator
        fake_lead = {
            "name": name,
            "scan_niche": lead.get("niche", ""),
            "scan_city": lead.get("city", ""),
        }
        email_content = generate_better_email(fake_lead)

        logger.info(f"[{i}/{len(leads)}] Sending to {name} <{to_email}>...")

        success = send_one_email(to_email, email_content["subject"], email_content["body"], dry_run)

        if success:
            sent_count += 1
            already_sent.append({
                "to": to_email,
                "name": name,
                "niche": lead.get("niche", ""),
                "subject": email_content["subject"],
                "sent_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
            sent_emails_set.add(to_email)
            # Wait between sends to avoid rate limiting
            if not dry_run:
                time.sleep(3)

    save_sent(already_sent)
    logger.info(f"Done! Sent {sent_count} emails.")
    logger.info(f"Total sent so far: {len(already_sent)}")
    return sent_count


def main():
    parser = argparse.ArgumentParser(description="Send outreach emails via Gmail")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be sent, don't send")
    parser.add_argument("--limit", type=int, help="Max emails to send")
    parser.add_argument("--niche", type=str, help="Only send to specific niche")
    args = parser.parse_args()

    print("=" * 60)
    print("  📧 EMAIL SENDER (Gmail SMTP)")
    print("=" * 60)

    if is_configured():
        print(f"  Gmail: {GMAIL_USER}")
        print(f"  Status: Ready to send")
    else:
        print(f"  Gmail: {GMAIL_USER or 'NOT SET'}")
        print(f"  App Password: {'SET' if GMAIL_APP_PASSWORD else 'NOT SET'}")
        print(f"  Status: Need configuration")
    print()

    send_outreach(limit=args.limit, dry_run=args.dry_run, niche=args.niche)


if __name__ == "__main__":
    main()
