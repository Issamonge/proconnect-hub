"""
MARKETPLACE LEAD COLLECTOR
=========================
Collects leads from the ProConnect Hub marketplace:
- Buyer leads (people needing services)
- Seller leads (businesses wanting customers)
- Renter leads (people needing property)

When a lead comes in:
1. Saves it to data/marketplace_leads.json
2. Sends notification email to you
3. For buyer leads: matches with 3 local businesses and notifies them
4. For seller leads: adds them to the seller database

Run this as a webhook receiver or check manually.

USAGE:
  python3 scripts/marketplace_leads.py serve      # Start webhook server on port 12001
  python3 scripts/marketplace_leads.py status      # Show lead stats
  python3 scripts/marketplace_leads.py notify      # Send notifications for pending leads
"""
import os
import sys
import json
import smtplib
import logging
import argparse
from datetime import datetime
from email.mime.text import MIMEText
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LEADS_FILE = os.path.join(DATA_DIR, "marketplace_leads.json")
SCAN_FILE = os.path.join(DATA_DIR, "scan_results.json")

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD", "")
BUSINESS_EMAIL = os.getenv("BUSINESS_EMAIL", GMAIL_USER)
WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "")


def load_leads():
    if not os.path.exists(LEADS_FILE):
        return []
    with open(LEADS_FILE) as f:
        return json.load(f)


def save_leads(leads):
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2)


def load_sellers():
    """Load existing businesses as potential sellers."""
    if not os.path.exists(SCAN_FILE):
        return []
    with open(SCAN_FILE) as f:
        return json.load(f)


def find_matching_sellers(service, city=""):
    """Find 3 businesses that match the buyer's service."""
    sellers = load_sellers()
    # First try exact niche match
    matches = [s for s in sellers if s.get("niche") == service and s.get("phone","").strip()]
    if not matches:
        matches = [s for s in sellers if s.get("niche") == service]
    return matches[:3]


def send_email(to_addr, subject, body):
    """Send an email via Gmail."""
    if not GMAIL_USER or not GMAIL_PASS:
        logger.warning("Gmail not configured, skipping email")
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
        logger.error(f"Email send failed: {e}")
        return False


def send_notification_to_owner(lead):
    """Send notification email to YOU when a new lead comes in."""
    lead_type = lead.get("type", "unknown")
    type_labels = {"buyer": "BUYER (needs service)", "seller": "SELLER (business signup)", "renter": "RENTER (property search)"}

    if lead_type == "buyer":
        body = f"""NEW LEAD — Someone needs a service!

Service needed: {lead.get('service','')}
City: {lead.get('city','')}
Description: {lead.get('description','N/A')}
Urgency: {lead.get('urgency','')}

Customer contact:
  Name: {lead.get('name','')}
  Phone: {lead.get('phone','')}
  Email: {lead.get('email','')}

ACTION NEEDED:
1. Contact the customer within 24 hours
2. Match them with businesses from your database
3. Notify the matched businesses (they pay you per lead)

Matched businesses from your database:
"""
        matches = find_matching_sellers(lead.get("service",""))
        for m in matches:
            body += f"  - {m.get('name','')} | {m.get('phone','')} | {m.get('location','')}\n"
        body += f"\n\nReply via WhatsApp: {WHATSAPP_NUMBER}" if WHATSAPP_NUMBER else ""

    elif lead_type == "seller":
        body = f"""NEW BUSINESS SIGNUP — A business wants leads!

Business: {lead.get('business','')}
Service: {lead.get('service','')}
City: {lead.get('city','')}
Phone: {lead.get('phone','')}
Email: {lead.get('email','')}
Plan: {lead.get('plan','')}

ACTION NEEDED:
1. Contact them to confirm and set up payment
2. Add them to your lead distribution list
3. Start sending them leads
"""
    elif lead_type == "renter":
        body = f"""NEW PROPERTY LEAD — Someone needs property!

Looking for: {lead.get('propertyType','')}
City: {lead.get('city','')}
Budget: {lead.get('budget','')}
Bedrooms: {lead.get('beds','')}
Timeline: {lead.get('timeline','')}

Contact:
  Name: {lead.get('name','')}
  Phone: {lead.get('phone','')}
  Email: {lead.get('email','')}

ACTION NEEDED:
1. Find matching properties or agents
2. Connect them directly
3. Charge finder's fee
"""
    else:
        body = f"Unknown lead type: {json.dumps(lead, indent=2)}"

    subject = f"[ProConnect Hub] New {type_labels.get(lead_type, lead_type)} Lead!"
    send_email(BUSINESS_EMAIL, subject, body)


def process_new_lead(lead_data):
    """Process a new lead from the marketplace."""
    lead = lead_data.copy()
    lead["id"] = f"LEAD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    lead["received_at"] = datetime.utcnow().isoformat()
    lead["status"] = "new"

    leads = load_leads()
    leads.append(lead)
    save_leads(leads)

    logger.info(f"New lead received: {lead['id']} ({lead.get('type','')})")

    # Send notification to owner
    send_notification_to_owner(lead)

    # For buyer leads, notify matched businesses
    if lead.get("type") == "buyer":
        matches = find_matching_sellers(lead.get("service",""))
        logger.info(f"  Matched with {len(matches)} businesses")

    return lead


def get_stats():
    """Get marketplace stats."""
    leads = load_leads()
    sellers = load_sellers()

    buyer_leads = [l for l in leads if l.get("type") == "buyer"]
    seller_leads = [l for l in leads if l.get("type") == "seller"]
    renter_leads = [l for l in leads if l.get("type") == "renter"]

    return {
        "total_leads": len(leads),
        "buyer_leads": len(buyer_leads),
        "seller_leads": len(seller_leads),
        "renter_leads": len(renter_leads),
        "total_sellers": len(sellers),
        "sellers_with_phone": len([s for s in sellers if s.get("phone","").strip()]),
    }


class LeadHandler(BaseHTTPRequestHandler):
    """HTTP handler for receiving leads from the marketplace."""

    def do_POST(self):
        if self.path == "/api/lead":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                lead_data = json.loads(body)
                lead = process_new_lead(lead_data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "lead_id": lead["id"]}).encode())
            except Exception as e:
                logger.error(f"Error processing lead: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == "/api/stats":
            stats = get_stats()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress default logging


def serve():
    """Start the webhook server."""
    port = int(os.getenv("MARKETPLACE_PORT", "12001"))
    server = HTTPServer(("0.0.0.0", port), LeadHandler)
    logger.info(f"Marketplace lead server running on port {port}")
    logger.info(f"  POST /api/lead   — receive new leads")
    logger.info(f"  GET  /api/stats  — get marketplace stats")
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Marketplace Lead Collector")
    parser.add_argument("command", choices=["serve", "status", "notify"], help="What to do")
    args = parser.parse_args()

    if args.command == "serve":
        serve()
    elif args.command == "status":
        stats = get_stats()
        print("=== MARKETPLACE STATS ===")
        print(f"  Buyer leads (need service):  {stats['buyer_leads']}")
        print(f"  Seller leads (businesses):   {stats['seller_leads']}")
        print(f"  Renter leads (need property): {stats['renter_leads']}")
        print(f"  Total leads:                  {stats['total_leads']}")
        print(f"  Sellers in database:          {stats['total_sellers']}")
        print(f"  Sellers with phone:           {stats['sellers_with_phone']}")
    elif args.command == "notify":
        leads = load_leads()
        pending = [l for l in leads if l.get("status") == "new"]
        logger.info(f"Processing {len(pending)} pending leads...")
        for lead in pending:
            send_notification_to_owner(lead)
            lead["status"] = "notified"
        save_leads(leads)
        logger.info("Done.")


if __name__ == "__main__":
    main()
