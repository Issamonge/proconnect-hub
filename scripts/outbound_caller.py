"""
OUTBOUND CALLER
===============
Makes AI voice calls to leads automatically using Bland AI.

The AI agent calls each lead, talks to them in English,
tries to qualify them and close the deal (or book a meeting).

USAGE:
  python3 scripts/outbound_caller.py              (call all new leads with phone numbers)
  python3 scripts/outbound_caller.py --limit 10   (call only 10 leads)
  python3 scripts/outbound_caller.py --dry-run     (show what would be called, no calls)
  python3 scripts/outbound_caller.py --test +123   (make one test call)

REQUIREMENTS:
  - BLAND_AI_API_KEY in .env (get it at https://bland.ai)
  - Leads found first: python3 scripts/lead_finder.py
"""
import os
import sys
import json
import time
import logging
import argparse
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lead_finder import get_leads_to_call, mark_lead_status
from bland_client import make_call, is_configured

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# How long to wait between calls (seconds) - to avoid spam detection
CALL_INTERVAL = int(os.getenv("CALL_INTERVAL_SECONDS", "60"))

CALLS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "call_results.json")
SCAN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "scan_results.json")


def save_call_record(call_id, lead_name, phone, niche):
    """Save a call record to track results."""
    record = {
        "call_id": call_id,
        "lead_name": lead_name,
        "phone": phone,
        "niche": niche,
        "status": "initiated",
        "called_at": __import__("datetime").datetime.utcnow().isoformat(),
        "result": None,
        "summary": None,
        "duration": None,
        "answered_by": None,
    }
    calls = []
    if os.path.exists(CALLS_FILE):
        try:
            with open(CALLS_FILE) as f:
                calls = json.load(f)
        except Exception:
            calls = []
    calls.append(record)
    with open(CALLS_FILE, "w") as f:
        json.dump(calls, f, indent=2)


def get_product_info():
    """Load product/business info from environment."""
    return {
        "business_name": os.getenv("BUSINESS_NAME", "Our Company"),
        "product_name": os.getenv("PRODUCT_NAME", "our service"),
        "product_price": os.getenv("PRODUCT_PRICE", ""),
        "product_description": os.getenv("PRODUCT_DESCRIPTION", ""),
        "payment_method": os.getenv("PAYMENT_METHOD_TEXT", "we'll send payment details by SMS"),
    }


def call_all_leads(limit=None, dry_run=False):
    """Call all new leads that have phone numbers."""
    if not is_configured():
        logger.error("Bland AI not configured. Set BLAND_AI_API_KEY in .env")
        logger.error("Get your key at https://bland.ai (regenerate it if you shared it before!)")
        return 0

    # Load leads from scan_results.json (primary data source)
    leads = []
    if os.path.exists(SCAN_FILE):
        with open(SCAN_FILE) as f:
            leads = json.load(f)
    else:
        # Fallback to found_leads.json
        leads = get_leads_to_call()

    # Filter to leads with phone numbers that haven't been called
    # Load previously called leads
    called_names = set()
    if os.path.exists(CALLS_FILE):
        try:
            with open(CALLS_FILE) as f:
                old_calls = json.load(f)
            called_names = {c.get("lead_name", "").lower() for c in old_calls}
        except Exception:
            pass

    leads_with_phone = [
        l for l in leads
        if l.get("phone", "").strip() and l.get("name", "").lower() not in called_names
    ]

    if not leads_with_phone:
        logger.info("No new leads with phone numbers to call.")
        logger.info(f"Total leads: {len(leads)}, with phone: {len([l for l in leads if l.get('phone','').strip()])}, already called: {len(called_names)}")
        return 0

    if limit:
        leads_with_phone = leads_with_phone[:limit]

    logger.info(f"Found {len(leads_with_phone)} leads to call")
    if dry_run:
        logger.info("DRY RUN - no actual calls will be made")
        for lead in leads_with_phone:
            logger.info(f"  Would call: {lead['name'][:50]} - {lead.get('phone')} ({lead.get('niche','')})")
        return len(leads_with_phone)

    product_info = get_product_info()
    logger.info(f"Calling {len(leads)} leads (waiting {CALL_INTERVAL}s between calls)...")
    logger.info(f"Business: {product_info['business_name']} | Product: {product_info['product_name']}")

    called = 0
    for i, lead in enumerate(leads, 1):
        phone = lead.get("phone", "")
        name = lead.get("name", "Unknown")
        niche = lead.get("niche", "")

        if not phone:
            logger.info(f"[{i}/{len(leads)}] {name} - no phone, skipping")
            continue

        # Normalize phone number to E.164 format
        clean_phone = phone.strip()
        if clean_phone and not clean_phone.startswith("+"):
            digits = "".join(c for c in clean_phone if c.isdigit())
            if len(digits) == 10:
                clean_phone = "+1" + digits
            elif len(digits) == 11 and digits[0] == "1":
                clean_phone = "+" + digits
            else:
                clean_phone = "+" + digits

        logger.info(f"[{i}/{len(leads)}] Calling {name} at {clean_phone} ({niche})...")
        call_id = make_call(clean_phone, name, product_info, niche=niche)

        if call_id:
            mark_lead_status(name, "called")
            called += 1
            # Save call record
            save_call_record(call_id, name, clean_phone, niche)
        else:
            mark_lead_status(name, "call_failed")

        # Wait between calls (don't call too fast)
        if i < len(leads):
            logger.info(f"Waiting {CALL_INTERVAL}s before next call...")
            time.sleep(CALL_INTERVAL)

    logger.info(f"Done. Called {called} leads.")
    return called


def make_test_call(phone_number):
    """Make a single test call."""
    if not is_configured():
        logger.error("Bland AI not configured. Set BLAND_AI_API_KEY in .env")
        return

    product_info = get_product_info()
    logger.info(f"Making test call to {phone_number}...")
    call_id = make_call(phone_number, "Test Lead", product_info)
    if call_id:
        logger.info(f"Test call started! Call ID: {call_id}")
        logger.info("Check results at https://app.bland.ai")
    else:
        logger.error("Test call failed.")


def main():
    parser = argparse.ArgumentParser(description="AI Outbound Caller (Bland AI)")
    parser.add_argument("--limit", type=int, help="Max leads to call")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be called without making calls")
    parser.add_argument("--test", type=str, help="Make a single test call to this number")
    args = parser.parse_args()

    print("=" * 50)
    print("  AI OUTBOUND CALLER (Bland AI)")
    print("=" * 50)

    if args.test:
        if not args.test.startswith("+"):
            print("ERROR: Phone number must start with country code (e.g. +1 for USA)")
            return
        make_test_call(args.test)
    else:
        call_all_leads(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
