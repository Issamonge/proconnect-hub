"""
FULL PIPELINE ORCHESTRATOR
==========================
The main system that runs the full cycle:

  1. SEARCH  → Find leads on the internet automatically
  2. CALL    → AI calls each lead in English, qualifies them
  3. CLOSE   → Close simple deals with payment links, book meetings for custom deals
  4. FOLLOW UP → Send SMS to leads, schedule retries
  5. REPORT  → Send you a summary of results

This can run:
  - Manually:   python3 scripts/pipeline.py
  - Scheduled:  as an OpenHands automation on a cron schedule (e.g. daily)

CONFIGURATION (in .env):
  LEAD_SEARCH_NICHE=plumber          (who to find)
  LEAD_SEARCH_LOCATION=Chicago, IL   (where to find them)
  LEAD_SEARCH_LIMIT=50               (how many per run)
  CALL_INTERVAL_SECONDS=60           (wait between calls)
  RUN_MODE=scheduled                 (scheduled = non-interactive)
"""
import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lead_finder import find_leads, get_leads_to_call, mark_lead_status
from lead_database import init_db, get_all_leads, get_qualified_leads
from deal_closer import get_closed_deals
from notifications import send_telegram_notification

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

RUN_MODE = os.getenv("RUN_MODE", "manual")
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "Our Business")


def step_find_leads(niche=None, location=None, limit=None):
    """Step 1: Search the internet for leads."""
    logger.info("=" * 50)
    logger.info("STEP 1: FINDING LEADS")
    logger.info("=" * 50)

    niche = niche or os.getenv("LEAD_SEARCH_NICHE", "plumber")
    location = location or os.getenv("LEAD_SEARCH_LOCATION", "Chicago, IL")
    limit = limit or int(os.getenv("LEAD_SEARCH_LIMIT", "50"))

    leads = find_leads(niche, location, limit)
    logger.info(f"Found {len(leads)} leads")
    return leads


def step_call_leads(limit=None, dry_run=False):
    """Step 2: AI calls the leads."""
    logger.info("=" * 50)
    logger.info("STEP 2: AI CALLING LEADS")
    logger.info("=" * 50)

    from outbound_caller import call_all_leads

    # Check if Bland AI is configured
    from bland_client import is_configured as bland_configured
    if not bland_configured():
        logger.warning("Bland AI not configured - skipping calls")
        logger.warning("Set BLAND_AI_API_KEY in .env to enable AI calling")
        return 0

    call_all_leads(limit=limit, dry_run=dry_run)

    leads_to_call = get_leads_to_call()
    return len(leads_to_call)


def step_follow_up():
    """Step 3: Follow up with qualified leads."""
    logger.info("=" * 50)
    logger.info("STEP 3: FOLLOWING UP WITH LEADS")
    logger.info("=" * 50)

    qualified = get_qualified_leads()
    logger.info(f"Found {len(qualified)} qualified leads to follow up with")

    twilio_configured = os.getenv("TWILIO_ACCOUNT_SID", "") not in ("", "your_twilio_account_sid")
    if not twilio_configured:
        logger.warning("Twilio not configured - skipping SMS follow-ups")
        return

    from sms_followup import send_followup_sms

    for lead in qualified:
        if lead.get("customer_phone"):
            send_followup_sms(lead["customer_phone"], {
                "customer_name": lead.get("customer_name", ""),
            })


def step_report(leads_found, leads_called):
    """Step 4: Send a summary report to the user."""
    logger.info("=" * 50)
    logger.info("STEP 4: SENDING REPORT")
    logger.info("=" * 50)

    all_leads = get_all_leads()
    closed_deals = get_closed_deals()

    report = f"📊 <b>PIPELINE REPORT - {BUSINESS_NAME}</b>\n\n"
    report += f"📅 Run time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += f"🔍 Leads found this run: {leads_found}\n"
    report += f"📞 Leads called this run: {leads_called}\n"
    report += f"📋 Total leads in database: {len(all_leads)}\n"
    report += f"✅ Qualified leads: {sum(1 for l in all_leads if l.get('qualified'))}\n"
    report += f"📅 Meetings booked: {sum(1 for l in all_leads if l.get('meeting_booked'))}\n"
    report += f"💰 Deals closed: {len(closed_deals)}\n"

    send_telegram_notification(report)
    logger.info("Report sent")


def run_full_pipeline(niche=None, location=None, limit=None, dry_run=False, skip_calls=False):
    """Run the complete pipeline: search → call → follow up → report."""
    logger.info("=" * 50)
    logger.info(f"  STARTING FULL PIPELINE - {BUSINESS_NAME}")
    logger.info("=" * 50)

    init_db()

    # Step 1: Find leads
    leads = step_find_leads(niche, location, limit)
    leads_found = len(leads)

    # Step 2: Call leads (unless skipped)
    leads_called = 0
    if not skip_calls:
        leads_called = step_call_leads(limit=limit, dry_run=dry_run)
    else:
        logger.info("Skipping calls (skip_calls=True)")

    # Step 3: Follow up
    step_follow_up()

    # Step 4: Report
    step_report(leads_found, leads_called)

    logger.info("=" * 50)
    logger.info("  PIPELINE COMPLETE")
    logger.info("=" * 50)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Full Lead-to-Deal Pipeline")
    parser.add_argument("--niche", help="Type of business to find (e.g. plumber)")
    parser.add_argument("--location", help="Where to find them (e.g. Chicago, IL)")
    parser.add_argument("--limit", type=int, help="Max leads per run")
    parser.add_argument("--dry-run", action="store_true", help="Find leads but don't call them")
    parser.add_argument("--find-only", action="store_true", help="Only find leads, don't call or follow up")
    args = parser.parse_args()

    if args.find_only:
        leads = step_find_leads(args.niche, args.location, args.limit)
        print(f"\nFound {len(leads)} leads:")
        for i, lead in enumerate(leads[:20], 1):
            print(f"  {i}. {lead['name']} | {lead.get('phone', 'no phone')}")
        return

    run_full_pipeline(
        niche=args.niche,
        location=args.location,
        limit=args.limit,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
