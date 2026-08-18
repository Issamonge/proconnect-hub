"""
WEBHOOK SERVER
==============
Receives call results from Vapi.ai when a call ends.

When a customer calls your AI agent:
1. Vapi sends the call result to this server
2. We save the lead in the database
3. We send you a notification (Telegram/email)
4. We send a follow-up SMS to the customer

HOW TO RUN:
1. Start the server:  python3 scripts/webhook_server.py
2. Expose it publicly:  run `ngrok http 8000` in another terminal
3. Copy the ngrok URL (e.g. https://abc123.ngrok.app)
4. Put it in your .env file as VAPI_SERVER_URL
5. In Vapi dashboard, set the webhook URL to: https://abc123.ngrok.app/webhook

NOTE: In production, deploy this to a real server (Railway, Fly.io, Render).
"""
import os
import sys
import json
import logging
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lead_database import init_db, save_call, get_qualified_leads

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Voice Agent Webhook Server")

NOTIFICATION_TELEGRAM_TOKEN = os.getenv("NOTIFICATION_TELEGRAM_BOT_TOKEN", "")
NOTIFICATION_TELEGRAM_CHAT_ID = os.getenv("NOTIFICATION_TELEGRAM_CHAT_ID", "")


def send_telegram_notification(message):
    """Send a notification to the user via Telegram."""
    if not NOTIFICATION_TELEGRAM_TOKEN or not NOTIFICATION_TELEGRAM_CHAT_ID:
        logger.info("Telegram not configured - skipping notification")
        return
    url = f"https://api.telegram.org/bot{NOTIFICATION_TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": NOTIFICATION_TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        requests.post(url, json=payload, timeout=10)
        logger.info("Telegram notification sent")
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")


def send_email_notification(subject, body):
    """Placeholder for email notification. Could use Resend, SendGrid, etc."""
    logger.info(f"Email notification (not sent): {subject}")


def format_lead_notification(structured_data, call_summary):
    """Format a notification message about a new lead."""
    name = structured_data.get("customer_name", "Unknown")
    phone = structured_data.get("customer_phone", "")
    interest = structured_data.get("product_interest", "Not specified")
    budget = structured_data.get("budget", "Not mentioned")
    timeline = structured_data.get("timeline", "Not mentioned")
    qualified = "YES" if structured_data.get("qualified") else "NO"
    meeting_booked = "YES" if structured_data.get("meeting_booked") else "NO"
    meeting_time = structured_data.get("meeting_time", "")
    outcome = structured_data.get("call_outcome", "unknown")

    msg = "📞 <b>NEW CALL FINISHED</b>\n\n"
    msg += f"👤 Customer: {name}\n"
    msg += f"📱 Phone: {phone}\n"
    msg += f"🛒 Interested in: {interest}\n"
    msg += f"💰 Budget: {budget}\n"
    msg += f"⏰ Timeline: {timeline}\n"
    msg += f"✅ Qualified: {qualified}\n"
    msg += f"📅 Meeting booked: {meeting_booked}"
    if meeting_time:
        msg += f" ({meeting_time})"
    msg += f"\n🎯 Outcome: {outcome}\n\n"
    msg += f"📋 Summary: {call_summary}\n"

    return msg


@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Database initialized")
    logger.info("Webhook server ready at /webhook")


@app.get("/")
async def root():
    return {"status": "ok", "service": "AI Voice Agent Webhook Server"}


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive call-end webhook from Bland AI (or Vapi)."""
    try:
        body = await request.json()
        logger.info(f"Received webhook: {str(body)[:200]}")

        # Bland AI sends: status, call_id, transcript, etc.
        # Vapi sends: type=end-of-call-report, message={...}
        call_data = {}

        if body.get("type") == "end-of-call-report":
            # Vapi format
            call_data = body.get("message", {})
            structured_data = save_call(call_data)
        else:
            # Bland AI format
            call_data = {
                "id": body.get("call_id", body.get("id", "")),
                "customer": {"number": body.get("to", body.get("phone_number", ""))},
                "analysis": {
                    "summary": body.get("summary", ""),
                    "structuredData": {
                        "customer_name": body.get("contact_name", ""),
                        "customer_phone": body.get("to", ""),
                        "product_interest": "",
                        "budget": "",
                        "timeline": "",
                        "qualified": body.get("qualified", False),
                        "meeting_booked": body.get("meeting_booked", False),
                        "call_outcome": body.get("outcome", body.get("status", "")),
                    },
                },
                "durationSeconds": body.get("call_length", 0),
            }
            structured_data = save_call(call_data)

        # Send notification in background
        summary = call_data.get("analysis", {}).get("summary", "No summary available")
        notification = format_lead_notification(structured_data, summary)
        background_tasks.add_task(send_telegram_notification, notification)

        # Close the deal based on the call outcome
        customer_phone = structured_data.get("customer_phone", "")
        customer_name = structured_data.get("customer_name", "")
        outcome = structured_data.get("call_outcome", "")

        # If the AI says the customer is ready to buy → send payment link
        if outcome == "closed" and customer_phone:
            from deal_closer import close_deal_simple
            product = structured_data.get("product_interest", "")
            background_tasks.add_task(
                close_deal_simple, customer_phone, customer_name, product
            )

        # If qualified but no meeting booked → send follow-up SMS
        elif structured_data.get("qualified") and not structured_data.get("meeting_booked"):
            from sms_followup import send_followup_sms
            if customer_phone:
                background_tasks.add_task(send_followup_sms, customer_phone, structured_data)

        # If meeting was booked → send confirmation SMS
        if structured_data.get("meeting_booked") and customer_phone:
            from sms_followup import send_booking_confirmation
            meeting_time = structured_data.get("meeting_time", "the scheduled time")
            background_tasks.add_task(
                send_booking_confirmation, customer_phone, meeting_time, customer_name
            )

        return JSONResponse({"status": "saved"})

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)


@app.get("/leads")
async def list_leads():
    """View all leads in the database."""
    from lead_database import get_all_leads
    leads = get_all_leads()
    return {"total": len(leads), "leads": leads}


@app.get("/leads/qualified")
async def list_qualified_leads():
    """View qualified leads that need follow-up."""
    leads = get_qualified_leads()
    return {"total": len(leads), "leads": leads}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting webhook server on port {port}")
    logger.info("Press Ctrl+C to stop")
    logger.info("Remember to run ngrok to expose this publicly:")
    logger.info("  ngrok http 8000")
    uvicorn.run(app, host="0.0.0.0", port=port)
