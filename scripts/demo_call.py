"""
DEMO CALL SCRIPT
================
Creates a live demo call that plumbers can listen to.

This makes a REAL call to any phone number using Bland AI,
so a plumber can hear exactly how the AI assistant sounds.

USAGE:
  python3 scripts/demo_call.py --to +12345678900
  python3 scripts/demo_call.py --to +12345678900 --niche dentist

The AI will:
  - Answer as if it's the plumber's business
  - Play the role of the AI assistant
  - Have a realistic conversation
  - Book a fake appointment

This lets the plumber HEAR the value before buying.
"""
import os
import sys
import logging
import argparse
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bland_client import make_call, is_configured

load_dotenv()

logging.basicConfig(level=logging=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)


DEMO_TASKS = {
    "plumber": """You are doing a LIVE DEMO of an AI voice assistant for a plumbing business.

This is a DEMO CALL — the person who answers is the plumber (the business owner), and they want to hear how the AI sounds from a customer's perspective.

Play BOTH roles in the conversation:
1. First, demonstrate how the AI ASSISTANT answers a call (be the AI)
2. Then ask the plumber to pretend to be a customer calling about a leak
3. Show them how the AI would handle it — book the appointment, ask for details

CONVERSATION FLOW:
- "Hi! This is a demo of your AI voice assistant. I'm going to show you how it works. Ready?"
- Wait for response
- "Great. Let me show you how I answer when a customer calls your business:"
- Demonstrate: "Hi, thanks for calling [their business]! How can I help you today?"
- Tell them: "Now YOU pretend to be a customer with a plumbing problem. Go ahead!"
- Let them speak, then respond as the AI would (ask about the problem, address, book a time)
- After the demo: "That's how your AI assistant works. It answers every call 24/7, books appointments, and texts you the details. Interested in setting this up? Reply to our email."

Keep it friendly, natural, and under 2 minutes.""",

    "electrician": """You are doing a LIVE DEMO of an AI voice assistant for an electrical business.

This is a DEMO CALL — the person who answers is the electrician (business owner) who wants to hear how the AI sounds.

Show them how the AI handles a customer call about an electrical emergency (power outage, sparking outlet).

CONVERSATION FLOW:
- "Hi! This is a demo of your AI voice assistant. I'll show you how it works."
- Demonstrate answering as their business: "Hi, thanks for calling! How can I help?"
- Ask them to pretend to be a customer with an electrical problem
- Respond as the AI: ask about the issue, assess urgency, book a visit
- End: "That's your AI assistant. It answers 24/7 and books jobs. Want to set it up? Reply to our email."

Keep it friendly, natural, under 2 minutes.""",

    "dentist": """You are doing a LIVE DEMO of an AI voice assistant for a dental practice.

This is a DEMO CALL — the person who answers is the dentist or office manager who wants to hear how the AI sounds.

Show them how the AI handles a new patient calling to book an appointment.

CONVERSATION FLOW:
- "Hi! This is a demo of your AI voice assistant for your dental practice."
- Demonstrate: "Hi, thanks for calling! How can I help you today?"
- Ask them to pretend to be a new patient wanting to book a cleaning
- Respond as the AI: ask if they're a new patient, book a slot, take their info
- End: "That's your AI assistant — it fills your schedule 24/7. Want to set it up? Reply to our email."

Keep it friendly, natural, under 2 minutes.""",

    "default": """You are doing a LIVE DEMO of an AI voice assistant for a small business.

This is a DEMO CALL — the person who answers is the business owner who wants to hear how the AI sounds.

CONVERSATION FLOW:
- "Hi! This is a demo of your AI voice assistant. I'll show you how it works."
- Demonstrate answering: "Hi, thanks for calling! How can I help you today?"
- Ask them to pretend to be a customer with a question or problem
- Respond as the AI: help them, book an appointment, take their details
- End: "That's your AI assistant — answers 24/7, books appointments. Want to set it up? Reply to our email."

Keep it friendly, natural, under 2 minutes.""",
}


def make_demo_call(phone_number, niche="plumber"):
    """Make a demo call to show a business owner how the AI sounds."""
    if not is_configured():
        logger.error("Bland AI not configured. Set BLAND_AI_API_KEY in .env")
        return None

    task = DEMO_TASKS.get(niche, DEMO_TASKS["default"])

    product_info = {
        "business_name": os.getenv("BUSINESS_NAME", "AI Pro Assist"),
        "product_name": "AI Voice Assistant",
        "product_price": "$500 setup + $200/month",
        "payment_method": "PayPal or crypto — details sent by email",
    }

    logger.info(f"Making DEMO call to {phone_number} (niche: {niche})...")
    call_id = make_call(phone_number, "Demo Lead", product_info, task=task)

    if call_id:
        logger.info(f"✅ Demo call started! Call ID: {call_id}")
        logger.info(f"The business owner will hear the AI assistant in action.")
        logger.info(f"Listen to the recording at https://app.bland.ai")
        return call_id
    else:
        logger.error("Demo call failed.")
        return None


def main():
    parser = argparse.ArgumentParser(description="Make a demo call to show a business owner how the AI works")
    parser.add_argument("--to", type=str, required=True, help="Phone number to call (with country code, e.g. +12345678900)")
    parser.add_argument("--niche", type=str, default="plumber", help="Business niche (plumber, dentist, electrician, etc.)")
    args = parser.parse_args()

    if not args.to.startswith("+"):
        print("ERROR: Phone number must start with country code (e.g. +1 for USA)")
        return

    print("=" * 60)
    print("  📞 DEMO CALL — Show business owners the AI in action")
    print("=" * 60)
    print(f"  Calling: {args.to}")
    print(f"  Niche: {args.niche}")
    print()

    make_demo_call(args.to, args.niche)


if __name__ == "__main__":
    main()
