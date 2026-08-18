"""
UNIFIED PIPELINE RUNNER
=======================
Runs the full money-making pipeline:
1. Fetch call results from Bland AI (check for interested leads)
2. Generate payment links for interested leads
3. Send payment links via email to interested leads
4. Send follow-up emails to non-responders
5. Update the dashboard with latest stats
6. Deploy updated dashboard to Vercel

USAGE:
  python3 scripts/pipeline_runner.py              # Run full pipeline
  python3 scripts/pipeline_runner.py --calls 5     # Make 5 new voice calls
  python3 scripts/pipeline_runner.py --check-only  # Just check results, no new calls
  python3 scripts/pipeline_runner.py --deploy      # Just redeploy dashboard
"""
import os
import sys
import json
import logging
import argparse
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from call_results import update_all_calls, get_call_summary
from payment_system import get_all_payments, get_payment_stats, format_payment_message

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD", "")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SENT_FILE = os.path.join(DATA_DIR, "sent_emails.json")
EXTRACTED_FILE = os.path.join(DATA_DIR, "extracted_emails.json")
SCAN_FILE = os.path.join(DATA_DIR, "scan_results.json")


def send_payment_email(lead_name, email_addr, payment):
    """Send payment link email to an interested lead."""
    if not email_addr or not GMAIL_USER:
        logger.warning(f"  No email for {lead_name}, skipping payment email")
        return False

    subject = f"AI Pro Assist — Payment Link ({payment['invoice_id']})"
    body = format_payment_message(payment)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = email_addr

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)
        server.quit()
        logger.info(f"  ✅ Payment email sent to {lead_name} <{email_addr}>")
        return True
    except Exception as e:
        logger.error(f"  ❌ Failed to send payment email to {email_addr}: {e}")
        return False


def find_email_for_lead(lead_name):
    """Find the email address for a lead from extracted emails."""
    if not os.path.exists(EXTRACTED_FILE):
        return ""
    with open(EXTRACTED_FILE) as f:
        extracted = json.load(f)
    for entry in extracted:
        if lead_name.lower() in entry.get("name", "").lower() or entry.get("name", "").lower() in lead_name.lower():
            emails = entry.get("emails", [])
            valid = [e for e in emails if "@" in e and "webp" not in e and "png" not in e and "jpg" not in e]
            if valid:
                return valid[0]
    return ""


def process_interested_leads():
    """Send payment emails to all interested leads."""
    calls_file = os.path.join(DATA_DIR, "call_results.json")
    if not os.path.exists(calls_file):
        logger.info("No calls file yet.")
        return 0

    with open(calls_file) as f:
        calls = json.load(f)

    interested = [c for c in calls if c.get("result") == "interested"]
    logger.info(f"Found {len(interested)} interested leads to process")

    sent = 0
    for call in interested:
        lead_name = call.get("lead_name", "")
        email_addr = find_email_for_lead(lead_name)

        # Find the payment record
        payments = get_all_payments()
        payment = None
        for p in payments:
            if p.get("lead_name") == lead_name:
                payment = p
                break

        if payment and payment.get("status") == "pending":
            if send_payment_email(lead_name, email_addr, payment):
                sent += 1
                call["payment_email_sent"] = True
                call["payment_email_sent_at"] = datetime.utcnow().isoformat()

    # Save updated calls
    with open(calls_file, "w") as f:
        json.dump(calls, f, indent=2)

    logger.info(f"Sent {sent} payment emails.")
    return sent


def run_pipeline(make_calls=0, check_only=False, deploy=False):
    """Run the full pipeline."""
    print("=" * 60)
    print("  AI PRO ASSIST — PIPELINE RUNNER")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # Step 1: Fetch call results
    logger.info("\n📡 STEP 1: Fetching call results from Bland AI...")
    results = update_all_calls()

    # Step 2: Send payment emails to interested leads
    logger.info("\n💰 STEP 2: Sending payment emails to interested leads...")
    sent = process_interested_leads()

    # Step 3: Make new calls if requested
    if make_calls > 0 and not check_only:
        logger.info(f"\n📞 STEP 3: Making {make_calls} new voice calls...")
        from outbound_caller import call_all_leads
        call_all_leads(limit=make_calls)
    else:
        logger.info("\n📞 STEP 3: Skipping new calls (use --calls N to make calls)")

    # Step 4: Summary
    logger.info("\n" + "=" * 60)
    logger.info("  PIPELINE SUMMARY")
    logger.info("=" * 60)

    call_summary = get_call_summary()
    payment_stats = get_payment_stats()

    print(f"  📞 Calls made:     {call_summary['total']}")
    print(f"     Interested:     {call_summary['interested']}")
    print(f"     Maybe:          {call_summary['maybe']}")
    print(f"     Voicemail:      {call_summary['voicemail']}")
    print(f"     No answer:      {call_summary['no_answer']}")
    print(f"     Not interested: {call_summary['not_interested']}")
    print()
    print(f"  💰 Payments:       {payment_stats['total']} invoices")
    print(f"     Pending:        {payment_stats['pending']} (${payment_stats['pending_amount']})")
    print(f"     Paid:           {payment_stats['paid']}")
    print(f"     Revenue:        ${payment_stats['revenue']}")
    print()
    print(f"  📧 Payment emails sent this run: {sent}")

    # Step 5: Deploy if requested
    if deploy:
        logger.info("\n🚀 Deploying updated dashboard to Vercel...")
        os.system("bash /workspace/project/scripts/deploy_vercel.sh")

    print("\n" + "=" * 60)
    print("  ✅ Pipeline complete!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Unified Pipeline Runner")
    parser.add_argument("--calls", type=int, default=0, help="Number of new voice calls to make")
    parser.add_argument("--check-only", action="store_true", help="Only check results, no new calls")
    parser.add_argument("--deploy", action="store_true", help="Deploy dashboard to Vercel after")
    args = parser.parse_args()

    run_pipeline(make_calls=args.calls, check_only=args.check_only, deploy=args.deploy)


if __name__ == "__main__":
    main()
