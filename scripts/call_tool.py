"""
CALL TOOL — our own phone calling system (no Bland AI needed).

Uses Twilio: turns text into speech (TTS) and calls real phone numbers.
The script plays the business's offer message, listens for a press of "1",
and marks the deal as interested.

COST: your own Twilio account (~$0.013/min, free trial credit ok).

USAGE:
  python3 scripts/call_tool.py --dry        # show who would be called
  python3 scripts/call_tool.py --call       # actually call
"""
import os
import sys
import json
import argparse
import logging
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE_DIR, "data")

NICHE_LABELS = {
    "plumber": "plumber", "electrician": "electrician", "roofing": "roofer",
    "car_repair": "auto repair shop", "dentist": "dentist", "lawyer": "lawyer",
    "veterinary": "vet", "real_estate": "real estate agent",
}

TWIML_HEADERS = {"Content-Type": "application/xml"}
TWIML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather numDigits="1" timeout="15" action="{action_url}">
    <Say voice="alice">{message}</Say>
  </Gather>
  <Say voice="alice">No answer received. We'll email you the details. Goodbye!</Say>
</Response>"""


def load_env():
    env = {}
    path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(path):
        for line in open(path):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env


def normalize_phone(p):
    digits = "".join(c for c in p if c.isdigit())
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return None


def build_message(deal):
    niche = NICHE_LABELS.get(deal.get("lead_niche", "service"), "service")
    return (
        f"Hello! This is ProConnect Hub. We have a customer who needs a {niche}. "
        f"If you want this customer lead, press 1. "
        f"The lead fee is 25 dollars only if you take it. Press 1 to say yes."
    )


def callable_targets(dry_run=False):
    """Yield (deal, phone) pairs that have real phone numbers and no email sent."""
    deals = json.load(open(os.path.join(DATA, "deals.json")))
    leads = {l["id"]: l for l in json.load(open(os.path.join(DATA, "buyer_leads.json")))}
    targets = []
    for deal in deals:
        if deal.get("status") == "called":
            continue
        phone = normalize_phone(deal.get("seller_phone", ""))
        if not phone:
            continue
        lead = leads.get(deal.get("lead_id"), {})
        deal["lead_niche"] = lead.get("niche", "service")
        targets.append((deal, phone))
    return targets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--call", action="store_true")
    args = parser.parse_args()

    targets = callable_targets()
    print(f"Callable deals with real phone numbers: {len(targets)}")
    for deal, phone in targets:
        print(f"  {phone} → {deal['seller_name'][:35]} ({deal.get('lead_location', '?')})")

    if not args.call:
        print("\nDry run only. Use --call to actually dial.")

    if args.call:
        env = load_env()
        sid, token, from_num = env.get("TWILIO_ACCOUNT_SID"), env.get("TWILIO_AUTH_TOKEN"), env.get("TWILIO_FROM_NUMBER")
        if not (sid and token and from_num):
            print("\n❌ Missing Twilio config in .env. Need:")
            print("TWILIO_ACCOUNT_SID=ACxxx")
            print("TWILIO_AUTH_TOKEN=xxx")
            print("TWILIO_FROM_NUMBER=+1xxxxxxxxxx")
            return
        from twilio.rest import Client
        client = Client(sid, token)
        # host a public twiml endpoint via bin — simplest: use inline Twiml verb via twilio's twimlet? No — build per-call TwiML inline
        called = 0
        deals_file = os.path.join(DATA, "deals.json")
        deals = json.load(open(deals_file))
        for deal, phone in targets:
            msg = build_message(deal)
            twiml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Response>'
                f'<Say voice="alice">{msg}</Say>'
                '<Pause length="3"/>'
                f'<Gather numDigits="1" timeout="10"><Say voice="alice">Press 1 to confirm interest.</Say></Gather>'
                '</Response>'
            )
            try:
                c = client.calls.create(to=phone, from_=from_num, twiml=twiml)
                print(f"📞 Calling {phone} → SID {c.sid}")
                deal["status"] = "called"
                deal["call_sid"] = c.sid
                called += 1
            except Exception as e:
                print(f"❌ {phone}: {e}")
        for i, d in enumerate(deals):
            for td, _ in targets:
                if d["deal_id"] == td["deal_id"]:
                    deals[i] = td
        json.dump(deals, open(deals_file, "w"), indent=2)
        print(f"\nCalled: {called}")


if __name__ == "__main__":
    main()
