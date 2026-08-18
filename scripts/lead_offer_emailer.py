"""
LEAD OFFER EMAILER
==================
Emails businesses that have email addresses, offering them customer leads.

For each business:
1. Finds matching buyer leads in our database
2. Sends email: "I have a customer who needs [service] in [city]. Lead fee $25."
3. Includes PayPal + crypto payment link
4. When they reply YES, we send them the buyer's contact info

USAGE:
  python3 scripts/lead_offer_emailer.py              # Send to all businesses with matching buyer leads
  python3 scripts/lead_offer_emailer.py --all        # Send to all businesses (general offer)
  python3 scripts/lead_offer_emailer.py --stats      # Show stats
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
EXTRACTED_EMAILS_FILE = os.path.join(DATA_DIR, "extracted_emails.json")
SCAN_FILE = os.path.join(DATA_DIR, "scan_results.json")
BUYER_LEADS_FILE = os.path.join(DATA_DIR, "buyer_leads.json")
DEALS_FILE = os.path.join(DATA_DIR, "deals.json")
SENT_OFFERS_FILE = os.path.join(DATA_DIR, "sent_lead_offers.json")

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD", "")

NICHE_LABELS = {
    "plumber": "plumbing",
    "electrician": "electrical",
    "roofing": "roofing",
    "car_repair": "auto repair",
    "dentist": "dental",
    "lawyer": "legal",
    "veterinary": "veterinary",
    "real_estate": "real estate",
}


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_business_email(name):
    """Find email for a business by name."""
    extracted = load_json(EXTRACTED_EMAILS_FILE)
    name_lower = name.lower()
    for entry in extracted:
        entry_name = entry.get("name", "").lower()
        # Try exact or partial match
        if name_lower in entry_name or entry_name in name_lower:
            for email in entry.get("emails", []):
                if "@" in email and not any(ext in email for ext in ["webp", "png", "jpg", "jpeg", "svg", "gif"]):
                    return email
    return ""


def find_buyer_leads_for_niche(niche):
    """Find buyer leads that match a business's niche."""
    buyer_leads = load_json(BUYER_LEADS_FILE)
    return [l for l in buyer_leads if l.get("niche") == niche and l.get("status") == "matched"]


def generate_offer_email(business_name, niche, buyer_leads, business_location=""):
    """Generate an email offering customer leads to a business."""
    niche_label = NICHE_LABELS.get(niche, niche.replace("_", " "))

    lead_summaries = []
    for bl in buyer_leads[:3]:
        location = bl.get("location", "")
        desc = bl.get("description", "")[:100]
        lead_summaries.append(f"  - Customer in {location or 'your area'}: {desc}")

    leads_text = "\n".join(lead_summaries) if lead_summaries else f"  - Customers in your area looking for {niche_label} services"

    num_leads = len(buyer_leads) if buyer_leads else "multiple"

    paypal_user = GMAIL_USER.split("@")[0] if GMAIL_USER else "proconnecthub"

    return f"""Hi {business_name},

I have {num_leads} customer{'s' if isinstance(num_leads, int) and num_leads != 1 else ''} looking for {niche_label} services right now. These are real people who posted online asking for recommendations.

Here's what they need:
{leads_text}

I'd like to send you their contact info (name, phone, email) so you can call them and quote the job.

Lead fee: $25 per customer
- Pay only for leads you want
- You get the customer's full contact info immediately after payment
- No subscription, no commitment

Pay here:
- PayPal: https://www.paypal.com/paypalme/{paypal_user}/25
- Crypto (BEP20): 0x27e16d0df86a051e1b14c0f5b90db76d74fd0704

Reply to this email with:
1. Which lead(s) you want
2. Payment confirmation

And I'll send you the customer's contact info within 1 hour.

Best regards,
ProConnect Hub
{GMAIL_USER}

P.S. I find new customers every day. Reply "YES" if you want me to keep sending you leads."""


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
        logger.error(f"Email to {to_addr} failed: {e}")
        return False


def send_lead_offers(all_businesses=False):
    """Send lead offer emails to businesses."""
    sellers = load_json(SCAN_FILE)
    sent_offers = load_json(SENT_OFFERS_FILE)
    sent_emails = {o.get("business_email") for o in sent_offers}

    # Group sellers by niche
    niches = {}
    for s in sellers:
        niche = s.get("niche", "")
        if niche:
            if niche not in niches:
                niches[niche] = []
            niches[niche].append(s)

    total_sent = 0
    total_skipped = 0

    for niche, businesses in niches.items():
        buyer_leads = find_buyer_leads_for_niche(niche)
        niche_label = NICHE_LABELS.get(niche, niche.replace("_", " "))

        if not buyer_leads and not all_businesses:
            continue

        logger.info(f"\n{'='*50}")
        logger.info(f"NICHE: {niche_label} — {len(businesses)} businesses, {len(buyer_leads)} buyer leads")

        for business in businesses:
            business_name = business.get("name", "")
            business_location = business.get("location", "")

            # Find email for this business
            email = get_business_email(business_name)
            if not email:
                continue

            if email in sent_emails:
                total_skipped += 1
                continue

            # Generate and send email
            subject = f"Customer lead available — {niche_label} work needed"
            body = generate_offer_email(business_name, niche, buyer_leads, business_location)

            logger.info(f"  Emailing: {business_name[:30]} <{email}>")

            if send_email(email, subject, body):
                offer = {
                    "business_name": business_name,
                    "business_email": email,
                    "niche": niche,
                    "location": business_location,
                    "leads_offered": len(buyer_leads),
                    "sent_at": now_utc(),
                    "status": "sent",
                }
                sent_offers.append(offer)
                total_sent += 1
                logger.info(f"    ✅ Sent — offering {len(buyer_leads)} leads")
            else:
                logger.warning(f"    ❌ Failed")

    save_json(SENT_OFFERS_FILE, sent_offers)
    logger.info(f"\n{'='*50}")
    logger.info(f"DONE: {total_sent} emails sent, {total_skipped} already contacted")
    return total_sent


def get_stats():
    sent = load_json(SENT_OFFERS_FILE)
    return {
        "total_sent": len(sent),
        "by_niche": {},
    }


def main():
    parser = argparse.ArgumentParser(description="Send customer lead offers to businesses")
    parser.add_argument("--all", action="store_true", help="Email all businesses (even without matching buyer leads)")
    parser.add_argument("--stats", action="store_true", help="Show stats")
    args = parser.parse_args()

    print("=" * 60)
    print("  PROCONNECT HUB - LEAD OFFER EMAILER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    if args.stats:
        sent = load_json(SENT_OFFERS_FILE)
        print(f"\n  Lead offer emails sent: {len(sent)}")
        by_niche = {}
        for o in sent:
            n = o.get("niche", "?")
            by_niche[n] = by_niche.get(n, 0) + 1
        for niche, count in sorted(by_niche.items()):
            print(f"    {niche}: {count}")
    else:
        send_lead_offers(all_businesses=args.all)


if __name__ == "__main__":
    main()
