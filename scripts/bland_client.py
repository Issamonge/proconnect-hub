"""
BLAND AI CLIENT
===============
Calls Bland AI to make outbound voice calls.

Bland AI is the voice agent platform (alternative to Vapi).
It makes AI phone calls that sound human.

SECURITY: The API key is read from environment variable BLAND_AI_API_KEY.
NEVER put your real API key in this file or in chat.
Put it in your .env file:
    BLAND_AI_API_KEY=your_key_here

API Docs: https://docs.bland.ai
"""
import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BLAND_AI_API_KEY = os.getenv("BLAND_AI_API_KEY", "")
BLAND_BASE_URL = "https://api.bland.ai/v1"

# The phone number you bought on Bland (or from_number Bland assigns)
BLAND_FROM_NUMBER = os.getenv("BLAND_FROM_NUMBER", "")


def is_configured():
    """Check if Bland AI is configured."""
    return bool(BLAND_AI_API_KEY) and BLAND_AI_API_KEY != "your_bland_api_key_here"


NICHE_PITCHES = {
    "plumber": "missed emergency calls. Every missed 2 AM burst pipe call is a $500+ job lost to whoever answers first. Our AI answers instantly 24/7, qualifies the emergency, and texts you the details so you never lose another job.",
    "electrician": "missed calls from customers needing urgent electrical work. Our AI answers every call 24/7, books appointments, and captures the job details so you never lose business to a competitor who picks up.",
    "dentist": "calls from patients wanting to book or asking about services. Our AI answers 24/7, schedules appointments directly into your calendar, and answers common questions about insurance and procedures.",
    "roofing": "calls from homeowners with roof damage who call the first company that answers. Our AI picks up every call 24/7, qualifies the lead, and texts you the job details so you can call them back and close.",
    "car_repair": "calls from stranded drivers and people needing quotes. Our AI answers 24/7, gives basic pricing info, and books them in so your bays stay full.",
    "lawyer": "potential clients calling after hours or when you're in court. Our AI captures every lead 24/7, takes down their case details, and texts you a summary so you can follow up before they call another firm.",
    "vet": "calls from worried pet owners. Our AI answers 24/7, triages emergencies, schedules appointments, and reassures clients so you never miss a worried pet parent.",
    "real_estate": "calls from buyers and sellers. Our AI answers 24/7, qualifies leads, captures property interests, and books showings so you never miss a hot lead.",
    "restaurant": "calls about hours, reservations, and menu questions. Our AI answers 24/7, takes reservations, and answers FAQs so you never miss a booking.",
}

DEFAULT_PITCH = "missed calls when you're busy or after hours. Our AI voice assistant answers every call 24/7 in perfect English, qualifies leads, books appointments, and texts you the details so you never lose another customer."


def make_call(to_number, lead_name, product_info, task=None, niche=None):
    """
    Make an outbound AI call to a lead using Bland AI.

    Args:
        to_number: Phone number to call (with country code, e.g. +12345678900)
        lead_name: Name of the business/person being called
        product_info: Dict with business_name, product_name, product_price, etc.
        task: Custom instructions for the AI (optional)
        niche: Lead's niche for a personalized pitch (optional)

    Returns:
        Call ID if successful, None if failed.
    """
    if not is_configured():
        logger.error("Bland AI not configured. Set BLAND_AI_API_KEY in .env")
        return None

    business = product_info.get("business_name", "AI Pro Assist")
    product = product_info.get("product_name", "24/7 AI Voice Assistant")
    price = product_info.get("product_price", "$500 setup + $200/month")
    payment_method = product_info.get("payment_method", "we'll send a payment link by text")
    pitch = NICHE_PITCHES.get(niche, DEFAULT_PITCH) if niche else DEFAULT_PITCH

    if not task:
        task = f"""You are Alex, calling from {business}. You're calling {lead_name}, a {niche or "local"} business.

YOUR GOAL: Get them interested in our 24/7 AI voice assistant and either close the sale or book a demo call.

IF YOU GET VOICEMAIL (you'll know because nobody picks up or you hear a voicemail greeting):
Leave this exact message: "Hi, this is Alex from AI Pro Assist. I'll keep this brief — we set up AI voice assistants for {niche or "local"} businesses so you never miss a customer call. The AI answers 24/7, books appointments, and sends you the details. It's {price} and live in 48 hours. If that sounds useful, give us a call back or reply to the email we sent you. Thanks, and have a great day!"
Then hang up. Do not wait on the line.

IF A HUMAN ANSWERS:

OPENING (be natural, friendly, confident):
"Hi, is the owner available? ... Hi, I'm Alex from AI Pro Assist. I'll keep this quick — do you have 30 seconds?"

PITCH (personalize to their business):
"We help {niche or "local"} businesses stop {pitch} The setup is {price} and it's live within 48 hours."

QUALIFY:
"Quick question — how many calls would you say your business misses each week?"
(Listen. Acknowledge. If they say few or none, ask "What about after hours or when you're on a job?")

CLOSE (pick one based on their response):
- If INTERESTED: "Great. I can send you a text right now with a payment link to get started, or I can book a 10-minute demo to show you exactly how it works. Which do you prefer?"
- If HESITANT: "Totally understand. Can I send you a quick text with a link to see a live demo? No pressure at all."
- If NOT INTERESTED: "No problem at all. I'll send a quick text with our info in case anything changes. Have a great day!"

RULES:
- Keep the call under 2 minutes.
- Sound human, not robotic. Use natural pauses like "hmm", "right", "got it".
- Never make up features or prices. If asked something you don't know: "Good question — I'll have our team follow up with the exact details."
- If they want to buy, say: "Awesome. I'm texting you a payment link right now. Once you complete it, we'll call you within 24 hours to set everything up."
- Payment details: {payment_method}
- Be respectful of their time. If they're busy, offer to text instead.
"""

    headers = {
        "Authorization": BLAND_AI_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "phone_number": to_number,
        "task": task,
        "voice": "josh",
        "wait_for_greeting": True,
        "record": True,
        "amd": True,
        "answered_by_enabled": True,
        "interruption_threshold": 100,
        "max_duration": 300,
        "model": "enhanced",
    }

    if BLAND_FROM_NUMBER:
        payload["from"] = BLAND_FROM_NUMBER

    try:
        response = requests.post(
            f"{BLAND_BASE_URL}/calls",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if response.status_code in (200, 201):
            data = response.json()
            call_id = data.get("call_id", data.get("id", ""))
            logger.info(f"Bland AI call started to {lead_name} ({to_number}) - ID: {call_id}")
            return call_id
        else:
            logger.error(f"Bland AI call failed: {response.status_code} {response.text}")
            return None
    except Exception as e:
        logger.error(f"Bland AI call error: {e}")
        return None


def get_call_details(call_id):
    """Get the details and results of a call."""
    if not is_configured():
        logger.error("Bland AI not configured.")
        return None

    headers = {"Authorization": BLAND_AI_API_KEY}
    try:
        response = requests.get(
            f"{BLAND_BASE_URL}/calls/{call_id}",
            headers=headers,
            timeout=15,
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get call {call_id}: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error getting call details: {e}")
        return None


def get_call_analysis(call_id):
    """Get the AI analysis of a call (did they want to buy? etc)."""
    details = get_call_details(call_id)
    if not details:
        return None

    return {
        "call_id": call_id,
        "status": details.get("status", ""),
        "duration": details.get("call_length", 0),
        "answered": details.get("answered_by", ""),
        "transcript": details.get("transcript", ""),
        "recording_url": details.get("recording_url", ""),
        "summary": details.get("summary", ""),
        "concatenated_transcript": details.get("concatenated_transcript", ""),
    }


if __name__ == "__main__":
    print("Bland AI Client Module")
    print(f"Configured: {is_configured()}")
    if is_configured():
        print("Ready to make calls.")
    else:
        print("Set BLAND_AI_API_KEY in your .env file.")
