"""
CALL RESULTS FETCHER
====================
Fetches call results from Bland AI and updates local records.

USAGE:
  python3 scripts/call_results.py           # Fetch and update all call results
  python3 scripts/call_results.py --summary  # Show summary only
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from payment_system import generate_payment_link, format_payment_message

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

BLAND_AI_API_KEY = os.getenv("BLAND_AI_API_KEY", "")
BLAND_BASE_URL = "https://api.bland.ai/v1"

CALLS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "call_results.json")
PAYMENTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "payments.json")


def load_calls():
    if not os.path.exists(CALLS_FILE):
        return []
    with open(CALLS_FILE) as f:
        return json.load(f)


def save_calls(calls):
    with open(CALLS_FILE, "w") as f:
        json.dump(calls, f, indent=2)


def fetch_call_details(call_id):
    """Fetch details for a single call from Bland AI."""
    try:
        r = requests.get(
            f"{BLAND_BASE_URL}/calls/{call_id}",
            headers={"Authorization": BLAND_AI_API_KEY},
            timeout=15,
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.error(f"Error fetching {call_id}: {e}")
    return None


def classify_call_result(details):
    """Classify a call as interested/not_interested/voicemail/no_answer."""
    answered = (details.get("answered_by") or "").lower()
    duration = details.get("call_length") or 0
    summary = (details.get("summary") or "").lower()
    transcript = (details.get("concatenated_transcript") or details.get("transcript") or "").lower()

    if "voicemail" in answered or "machine" in answered:
        return "voicemail"
    if duration < 5:
        return "no_answer"
    if any(w in summary for w in ["interested", "payment", "demo", "sign up", "yes", "sure", "sounds good"]):
        return "interested"
    if any(w in summary for w in ["not interested", "no thanks", "not now", "don't", "hang up"]):
        return "not_interested"
    if duration > 15:
        return "maybe"
    return "no_answer"


def update_all_calls():
    """Fetch updated results for all tracked calls."""
    calls = load_calls()
    if not calls:
        logger.info("No calls to update. Run outbound_caller.py first.")
        return

    logger.info(f"Updating {len(calls)} call records from Bland AI...")
    updated = 0
    interested = 0

    for call in calls:
        if call.get("status") in ("completed", "failed"):
            continue
        cid = call.get("call_id")
        if not cid:
            continue

        details = fetch_call_details(cid)
        if not details:
            continue

        result = classify_call_result(details)
        call["status"] = "completed" if details.get("status") == "completed" else details.get("status", "unknown")
        call["result"] = result
        call["summary"] = details.get("summary", "")
        call["duration"] = details.get("call_length", 0)
        call["answered_by"] = details.get("answered_by", "")
        call["transcript"] = (details.get("concatenated_transcript") or details.get("transcript") or "")[:2000]
        call["recording_url"] = details.get("recording_url", "")
        call["updated_at"] = datetime.utcnow().isoformat()
        updated += 1

        if result == "interested":
            interested += 1
            logger.info(f"  🎯 INTERESTED: {call['lead_name']} - {call['phone']}")
            logger.info(f"     Summary: {call['summary'][:100]}")
            # Auto-generate payment link for interested leads
            create_payment_for_lead(call)
        elif result == "voicemail":
            logger.info(f"  📞 Voicemail: {call['lead_name']}")
        elif result == "no_answer":
            logger.info(f"  ❌ No answer: {call['lead_name']}")
        else:
            logger.info(f"  📋 {result}: {call['lead_name']}")

    save_calls(calls)
    logger.info(f"Updated {updated} calls. {interested} interested leads found.")

    # Print summary
    results = {}
    for c in calls:
        r = c.get("result", "pending")
        results[r] = results.get(r, 0) + 1
    logger.info(f"Summary: {results}")
    return results


def create_payment_for_lead(call):
    """Auto-generate payment link for an interested lead."""
    # Check if payment already exists
    if os.path.exists(PAYMENTS_FILE):
        with open(PAYMENTS_FILE) as f:
            payments = json.load(f)
        for p in payments:
            if p.get("lead_name") == call.get("lead_name"):
                logger.info(f"  Payment already exists for {call['lead_name']}")
                return p

    payment = generate_payment_link(call.get("lead_name", "Unknown"), "")
    logger.info(f"  💰 Payment link created: {payment['invoice_id']}")
    logger.info(f"     PayPal: {payment['links']['paypal']}")
    return payment


def get_call_summary():
    """Get summary of all calls."""
    calls = load_calls()
    total = len(calls)
    results = {}
    for c in calls:
        r = c.get("result", "pending")
        results[r] = results.get(r, 0) + 1
    return {
        "total": total,
        "results": results,
        "interested": results.get("interested", 0),
        "voicemail": results.get("voicemail", 0),
        "no_answer": results.get("no_answer", 0),
        "maybe": results.get("maybe", 0),
        "not_interested": results.get("not_interested", 0),
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch Bland AI call results")
    parser.add_argument("--summary", action="store_true", help="Show summary only")
    args = parser.parse_args()

    if args.summary:
        s = get_call_summary()
        print("=== CALL SUMMARY ===")
        print(f"  Total calls: {s['total']}")
        print(f"  Interested: {s['interested']}")
        print(f"  Maybe: {s['maybe']}")
        print(f"  Voicemail: {s['voicemail']}")
        print(f"  No answer: {s['no_answer']}")
        print(f"  Not interested: {s['not_interested']}")
    else:
        update_all_calls()


if __name__ == "__main__":
    main()
