"""
DEAL CLOSER
===========
Closes deals by connecting buyers/renters with businesses.

For each matched lead:
1. Generates a Reddit reply/comment connecting the buyer with businesses
2. Generates an email to the matched businesses (they pay you for the lead)
3. Sends notification to you with all details
4. Tracks deal status

USAGE:
  python3 scripts/deal_closer.py                # Process all matched leads
  python3 scripts/deal_closer.py --stats        # Show deal stats
  python3 scripts/deal_closer.py --emails       # Send emails to businesses
"""
import os
import sys
import json
import smtplib
import logging
import argparse
from datetime import datetime, timezone
from email.mime.text import MIMEText
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
BUYER_LEADS_FILE = os.path.join(DATA_DIR, "buyer_leads.json")
DEALS_FILE = os.path.join(DATA_DIR, "deals.json")
SCAN_FILE = os.path.join(DATA_DIR, "scan_results.json")

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD", "")
BUSINESS_EMAIL = os.getenv("BUSINESS_EMAIL", GMAIL_USER)
WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "")

NICHE_LABELS = {
    "plumber": "plumber",
    "electrician": "electrician",
    "roofing": "roofer",
    "car_repair": "auto repair shop",
    "dentist": "dentist",
    "lawyer": "lawyer",
    "veterinary": "vet",
    "real_estate": "real estate agent",
}


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_buyer_leads():
    if not os.path.exists(BUYER_LEADS_FILE):
        return []
    with open(BUYER_LEADS_FILE) as f:
        return json.load(f)


def load_deals():
    if not os.path.exists(DEALS_FILE):
        return []
    with open(DEALS_FILE) as f:
        return json.load(f)


def save_deals(deals):
    with open(DEALS_FILE, "w") as f:
        json.dump(deals, f, indent=2)


def generate_reddit_reply(lead):
    niche = lead.get("niche", "service")
    niche_label = NICHE_LABELS.get(niche, niche.replace("_", " "))
    location = lead.get("location", "")
    matches = lead.get("matched_sellers", [])

    if not matches:
        return f"Hey! I run a platform called ProConnect Hub that connects people with local {niche_label}s. What area are you in? I can check our network and send you some options with free quotes. Feel free to DM me!"

    seller_lines = []
    for i, m in enumerate(matches, 1):
        name = m.get("name", "")[:40]
        phone = m.get("phone", "")
        loc = m.get("location", "")
        if phone:
            seller_lines.append(f"{i}. {name} - {phone} ({loc})")
        else:
            seller_lines.append(f"{i}. {name} ({loc})")
    sellers_text = "\n".join(seller_lines)
    location_note = f" in {location}" if location else " in your area"

    return f"""Hey! I run a platform called ProConnect Hub — we connect people with verified local pros. Here are some {niche_label}s{location_note} who can help:

{sellers_text}

They all do free quotes. Hope this helps! If you need anything else, feel free to DM me."""


def generate_business_email(lead, seller):
    niche = lead.get("niche", "service")
    niche_label = NICHE_LABELS.get(niche, niche.replace("_", " "))
    location = lead.get("location", "")
    buyer_desc = lead.get("description", "")
    paypal_user = GMAIL_USER.split("@")[0] if GMAIL_USER else "proconnect"

    return f"""Hi {seller.get('name','')},

I have a customer who needs a {niche_label} in {location or "your area"}.

Here's what they need:
"{buyer_desc}"

This is a qualified lead — they're actively looking for someone right now.

Would you like me to connect you with this customer?

Lead fee: $25 (pay only if you want the customer's contact info)

If yes, reply to this email or pay the lead fee here:
- PayPal: https://www.paypal.com/paypalme/{paypal_user}/25
- Crypto (BEP20): 0x27e16d0df86a051e1b14c0f5b90db76d74fd0704

Once payment is confirmed, I'll send you the customer's name, phone, and email immediately.

Best regards,
ProConnect Hub
{GMAIL_USER}"""


def send_email(to_addr, subject, body):
    if not GMAIL_USER or not GMAIL_PASS:
        logger.warning("Gmail not configured")
        return False
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = GMAIL_USER
        msg["To"] = to_addr
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False


def load_seller_emails():
    emails_file = os.path.join(DATA_DIR, "extracted_emails.json")
    if not os.path.exists(emails_file):
        return {}
    with open(emails_file) as f:
        extracted = json.load(f)
    email_map = {}
    for entry in extracted:
        name = entry.get("name", "")
        for email in entry.get("emails", []):
            if "@" in email and "webp" not in email and "png" not in email and "jpg" not in email:
                email_map[name.lower()] = email
                break
    return email_map


def process_all_deals(send_emails=False):
    leads = load_buyer_leads()
    deals = load_deals()
    existing_ids = {d.get("lead_id") for d in deals}

    matched = [l for l in leads if l.get("status") == "matched" and l.get("id") not in existing_ids]

    if not matched:
        logger.info("No new matched leads to process.")
        return 0

    seller_emails = load_seller_emails()
    logger.info(f"Processing {len(matched)} new matched leads...")

    new_deals = 0
    for lead in matched:
        niche = lead.get("niche", "service")
        niche_label = NICHE_LABELS.get(niche, niche.replace("_", " "))
        reddit_reply = generate_reddit_reply(lead)

        logger.info(f"\n{'='*60}")
        logger.info(f"LEAD: {lead['title'][:60]}")
        logger.info(f"URL: {lead['url']}")
        logger.info(f"Location: {lead.get('location', 'unknown')}")
        logger.info(f"Matched with {len(lead.get('matched_sellers', []))} businesses")
        logger.info(f"\nREDDIT REPLY:")
        logger.info(f"{'-'*50}")
        for line in reddit_reply.split("\n"):
            logger.info(f"  {line}")
        logger.info(f"{'-'*50}")

        for seller in lead.get("matched_sellers", []):
            seller_name = seller.get("name", "")
            seller_email = seller_emails.get(seller_name.lower(), "")

            deal = {
                "deal_id": f"DEAL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{new_deals}",
                "lead_id": lead.get("id"),
                "lead_title": lead.get("title"),
                "lead_url": lead.get("url"),
                "lead_location": lead.get("location"),
                "lead_description": lead.get("description"),
                "seller_name": seller_name,
                "seller_phone": seller.get("phone", ""),
                "seller_email": seller_email,
                "lead_fee": 25,
                "status": "pending_contact",
                "created_at": now_utc(),
                "reddit_reply": reddit_reply,
            }

            if send_emails and seller_email:
                subject = f"New customer lead in {lead.get('location', 'your area')} - {niche_label} needed"
                body = generate_business_email(lead, seller)
                if send_email(seller_email, subject, body):
                    deal["status"] = "email_sent"
                    deal["email_sent_at"] = now_utc()
                    logger.info(f"  Email sent to {seller_name} <{seller_email}>")
                else:
                    logger.warning(f"  Email failed to {seller_email}")
            elif seller_email:
                logger.info(f"  Email ready for {seller_name} <{seller_email}> (use --emails to send)")
            else:
                logger.info(f"  No email for {seller_name}, call: {seller.get('phone','')}")

            deals.append(deal)
            new_deals += 1

    save_deals(deals)
    logger.info(f"\n{'='*60}")
    logger.info(f"Created {new_deals} deals from {len(matched)} leads")
    logger.info(f"Total deals in database: {len(deals)}")
    return new_deals


def get_stats():
    deals = load_deals()
    leads = load_buyer_leads()
    pending = [d for d in deals if d.get("status") == "pending_contact"]
    emailed = [d for d in deals if d.get("status") == "email_sent"]
    paid = [d for d in deals if d.get("status") == "paid"]
    return {
        "total_deals": len(deals),
        "pending": len(pending),
        "emailed": len(emailed),
        "paid": len(paid),
        "total_leads": len(leads),
        "matched_leads": len([l for l in leads if l.get("status") == "matched"]),
        "potential_revenue": len(deals) * 25,
        "actual_revenue": len(paid) * 25,
    }


def main():
    parser = argparse.ArgumentParser(description="Close deals by connecting buyers with businesses")
    parser.add_argument("--stats", action="store_true", help="Show deal stats")
    parser.add_argument("--emails", action="store_true", help="Send emails to businesses")
    args = parser.parse_args()

    print("=" * 60)
    print("  PROCONNECT HUB - DEAL CLOSER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    if args.stats:
        s = get_stats()
        print(f"\n  Buyer/Renter leads found: {s['total_leads']}")
        print(f"  Matched with businesses:  {s['matched_leads']}")
        print(f"\n  Deals created:            {s['total_deals']}")
        print(f"  Pending contact:          {s['pending']}")
        print(f"  Emails sent:              {s['emailed']}")
        print(f"  Paid:                     {s['paid']}")
        print(f"\n  Potential revenue:        ${s['potential_revenue']}")
        print(f"  Actual revenue:           ${s['actual_revenue']}")
    else:
        process_all_deals(send_emails=args.emails)


if __name__ == "__main__":
    main()
