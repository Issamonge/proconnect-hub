"""
DAILY AUTOMATED RUNNER
======================
Runs the ENTIRE pipeline automatically, every day:
1. Find new leads (different cities each day)
2. Extract emails from their websites
3. Send outreach emails
4. Notify you via Telegram

This is the "set it and forget it" script.
Set up a cron job or OpenHands automation to run this daily.

USAGE:
  python3 scripts/daily_runner.py                (run full daily cycle)
  python3 scripts/daily_runner.py --dry-run       (preview, don't send)
  python3 scripts/daily_runner.py --no-find       (skip finding, just email existing leads)
  python3 scripts/daily_runner.py --emails-only   (just send emails to existing leads)

SETUP FOR DAILY AUTOMATION:
  Option A - OpenHands Automation (cloud, runs even when your PC is off):
    Set up via the automation API — runs daily in the cloud.

  Option B - Cron job on your computer (free, but PC must be on):
    crontab -e
    Add: 0 9 * * * cd /path/to/project && python3 scripts/daily_runner.py
    (runs every day at 9 AM)

REQUIREMENTS:
  - GMAIL_USER and GMAIL_APP_PASSWORD in .env (for sending emails)
  - Optional: TELEGRAM_BOT_TOKEN (for notifications)
  - Leads will be found automatically
"""
import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data",
                "daily_runner.log",
            )
        ),
    ],
)
logger = logging.getLogger(__name__)

# Rotate cities daily to find new leads
ALL_CITIES = [
    # US cities
    "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Miami, FL",
    "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA", "Dallas, TX",
    "San Jose, CA", "Austin, TX", "Jacksonville, FL", "Columbus, OH", "Indianapolis, IN",
    "Charlotte, NC", "Fort Worth, TX", "Detroit, MI", "Seattle, WA", "Denver, CO",
    "Boston, MA", "Portland, OR", "Las Vegas, NV", "Atlanta, GA", "Minneapolis, MN",
    "Nashville, TN", "Tucson, AZ", "New Orleans, LA", "Albuquerque, NM", "Memphis, TN",
    # UK cities (English-speaking, good for AI voice)
    "London, UK", "Manchester, UK", "Birmingham, UK", "Leeds, UK", "Bristol, UK",
    "Liverpool, UK", "Sheffield, UK", "Edinburgh, UK", "Glasgow, UK", "Cardiff, UK",
    # Canada cities
    "Toronto, Canada", "Vancouver, Canada", "Montreal, Canada", "Calgary, Canada", "Ottawa, Canada",
    # Australia cities
    "Sydney, Australia", "Melbourne, Australia", "Brisbane, Australia", "Perth, Australia", "Adelaide, Australia",
    # Ireland
    "Dublin, Ireland", "Cork, Ireland",
    # New Zealand
    "Auckland, New Zealand", "Wellington, New Zealand",
    # UAE / Middle East (English is business language)
    "Dubai, UAE", "Abu Dhabi, UAE", "Doha, Qatar", "Riyadh, Saudi Arabia",
    # Singapore / Asia (English-speaking business)
    "Singapore", "Hong Kong", "Kuala Lumpur, Malaysia",
]

NICHES = ["plumber", "electrician", "dentist", "restaurant", "hairdresser"]


def step_find_leads(dry_run=False, cities_per_day=3):
    """Step 1: Find new leads. Rotates cities each day."""
    from hot_lead_scanner import scan_all_niches, NICHES as SCANNER_NICHES

    # Pick 3 cities based on day of year (rotates daily)
    day_of_year = datetime.now().timetuple().tm_yday
    start = (day_of_year * 3) % len(ALL_CITIES)
    today_cities = []
    for i in range(cities_per_day):
        idx = (start + i) % len(ALL_CITIES)
        today_cities.append(ALL_CITIES[idx])

    niche_names = [n["name"] if isinstance(n, dict) else n for n in SCANNER_NICHES]

    logger.info(f"STEP 1: FINDING LEADS")
    logger.info(f"Cities for today: {', '.join(today_cities)}")
    logger.info(f"Niches: {', '.join(niche_names)}")

    if dry_run:
        logger.info("[DRY RUN] Skipping lead finding")
        return 0

    leads = scan_all_niches(limit_per_niche=5, cities=today_cities)
    logger.info(f"Found {len(leads)} new leads")
    return len(leads)


def step_extract_emails(dry_run=False, limit=50):
    """Step 2: Extract emails from the websites of found leads."""
    from email_extractor import extract_all_emails

    logger.info(f"STEP 2: EXTRACTING EMAILS FROM WEBSITES")

    if dry_run:
        logger.info("[DRY RUN] Skipping email extraction")
        return 0

    results = extract_all_emails(limit=limit, update_scan=True)
    logger.info(f"Found emails for {len(results)} businesses")
    return len(results)


def step_send_emails(dry_run=False, limit=50):
    """Step 3: Send outreach emails."""
    from email_sender import send_outreach, is_configured

    logger.info(f"STEP 3: SENDING OUTREACH EMAILS")

    if not is_configured():
        logger.warning("Gmail not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD in .env")
        logger.warning("Skipping email sending. You can still send manually.")
        return 0

    sent = send_outreach(limit=limit, dry_run=dry_run)
    logger.info(f"Sent {sent} emails today")
    return sent


def step_notify(summary):
    """Step 4: Send a notification with today's results."""
    from notifications import send_telegram_notification

    message = f"""📊 DAILY AUTOMATION REPORT
━━━━━━━━━━━━━━━━━━━━━━
{summary}
━━━━━━━━━━━━━━━━━━━━━━
The system is working automatically.
Check your email for replies from businesses."""

    logger.info("STEP 4: SENDING NOTIFICATION")
    send_telegram_notification(message)


def run_daily_cycle(dry_run=False, no_find=False, emails_only=False):
    """Run the complete daily automation cycle."""
    logger.info("=" * 60)
    logger.info("  🤖 DAILY AUTOMATED RUNNER")
    logger.info(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 60)

    leads_found = 0
    emails_extracted = 0
    emails_sent = 0

    # Step 1: Find leads
    if not no_find and not emails_only:
        leads_found = step_find_leads(dry_run)

    # Step 2: Extract emails
    if not emails_only:
        emails_extracted = step_extract_emails(dry_run, limit=50)

    # Step 3: Send emails
    emails_sent = step_send_emails(dry_run, limit=50)

    # Step 4: Notify
    summary = f"""Leads found: {leads_found}
Emails extracted: {emails_extracted}
Emails sent: {emails_sent}
"""
    step_notify(summary)

    # Step 5: Update dashboard
    try:
        logger.info("STEP 5: UPDATING DASHBOARD")
        from dashboard import generate_dashboard
        generate_dashboard()
    except Exception as e:
        logger.warning(f"Dashboard update failed: {e}")

    # Step 6: Check for replies and auto-respond
    try:
        logger.info("STEP 6: CHECKING FOR REPLIES (AUTO-REPLYER)")
        from auto_replyer import process_replies
        replies_sent, deals_ready = process_replies()
        if deals_ready > 0:
            logger.info(f"🔔 {deals_ready} deal(s) ready! Check Telegram/notifications.")
    except Exception as e:
        logger.warning(f"Auto-replyer failed: {e}")

    logger.info("=" * 60)
    logger.info("  ✅ DAILY CYCLE COMPLETE")
    logger.info(f"  Leads found: {leads_found}")
    logger.info(f"  Emails extracted: {emails_extracted}")
    logger.info(f"  Emails sent: {emails_sent}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Daily Automated Runner")
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending")
    parser.add_argument("--no-find", action="store_true", help="Skip finding new leads")
    parser.add_argument("--emails-only", action="store_true", help="Only send emails to existing leads")
    args = parser.parse_args()

    run_daily_cycle(
        dry_run=args.dry_run,
        no_find=args.no_find,
        emails_only=args.emails_only,
    )


if __name__ == "__main__":
    main()
