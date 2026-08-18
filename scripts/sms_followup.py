"""
SMS FOLLOW-UP
=============
Sends automatic SMS follow-ups to leads after a call.
Uses Twilio for SMS (https://www.twilio.com).
"""
import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "Our team")
CALENDAR_LINK = os.getenv("YOUR_CALENDAR_LINK", "")

twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_ACCOUNT_SID != "your_twilio_account_sid":
    try:
        from twilio.rest import Client
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    except ImportError:
        logger.warning("Twilio package not installed. Run: pip install twilio")


def send_sms(to_number, message):
    """Send an SMS to a phone number."""
    if not twilio_client:
        logger.info(f"[SMS not configured] To: {to_number} | Message: {message}")
        return False
    try:
        twilio_client.messages.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            body=message,
        )
        logger.info(f"SMS sent to {to_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_number}: {e}")
        return False


def send_followup_sms(customer_phone, structured_data):
    """Send a follow-up SMS after a qualified call."""
    name = structured_data.get("customer_name", "")
    greeting = f"Hi {name}," if name else "Hi,"

    # If we have a calendar link, include it
    if CALENDAR_LINK:
        message = (
            f"{greeting} Thanks for calling {BUSINESS_NAME}! "
            f"It was great speaking with you. "
            f"To book a meeting with our team, pick a time here: {CALENDAR_LINK} "
            f"Feel free to reply to this message with any questions."
        )
    else:
        message = (
            f"{greeting} Thanks for calling {BUSINESS_NAME}! "
            f"It was great speaking with you. "
            f"Our team will follow up with you shortly. "
            f"Feel free to reply to this message with any questions."
        )

    return send_sms(customer_phone, message)


def send_booking_confirmation(customer_phone, meeting_time, name=""):
    """Send a confirmation SMS when a meeting is booked."""
    greeting = f"Hi {name}," if name else "Hi,"
    message = (
        f"{greeting} Your meeting with {BUSINESS_NAME} is confirmed "
        f"for {meeting_time}. "
        f"We'll send you a reminder before the meeting. Looking forward to it!"
    )
    return send_sms(customer_phone, message)


if __name__ == "__main__":
    print("SMS Follow-up Module")
    print("=" * 30)
    if not twilio_client:
        print("Twilio not configured. Set TWILIO_* values in .env")
        print("This is optional - the system works without SMS too.")
    else:
        test_number = input("Enter a phone number to test SMS (or press Enter to skip): ")
        if test_number:
            send_sms(test_number, f"Test message from {BUSINESS_NAME} AI system.")
            print("Test SMS sent!")
