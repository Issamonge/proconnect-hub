"""
REPLY HANDLER
=============
Helps you handle replies from businesses WITHOUT speaking English.

When a business replies to your outreach email, you:
  1. Copy their reply
  2. Run: python3 scripts/reply_handler.py
  3. Paste their message
  4. The system suggests the perfect response in English
  5. You copy-paste the response and send it

This means you NEVER have to write English yourself.

USAGE:
  python3 scripts/reply_handler.py
  (then paste the business's reply when prompted)
"""
import os
import sys
import json
import logging
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

BUSINESS_NAME = os.getenv("BUSINESS_NAME", "AI Pro Assist")
YOUR_EMAIL = os.getenv("BUSINESS_EMAIL", "")
PAYPAL_EMAIL = os.getenv("PAYPAL_EMAIL", "")
CRYPTO_USDT = os.getenv("CRYPTO_USDT_ADDRESS", "")
WHATSAPP_LINK = os.getenv("WHATSAPP_LINK", "")
BUSINESS_PHONE = os.getenv("BUSINESS_PHONE", "")
PRODUCT_PRICE = os.getenv("PRODUCT_PRICE", "$500 setup + $200/month")
GMAIL_USER = os.getenv("GMAIL_USER", "")

# PayPal link for lead payments
PAYPAL_LEAD_LINK = f"https://www.paypal.com/paypalme/{GMAIL_USER.split('@')[0]}/25" if GMAIL_USER else "https://www.paypal.com/paypalme/proconnecthub/25"

# WhatsApp contact line (added to all responses)
WHATSAPP_LINE = f"\n💬 WhatsApp: {WHATSAPP_LINK}" if WHATSAPP_LINK else ""


# Pre-written responses for common reply types
RESPONSES = {
    "yes": f"""Great, thanks for getting back to me!

Here's how it works:

1. I set up an AI voice assistant for your business
2. It answers every call 24/7 in perfect English
3. It books appointments directly into your calendar
4. It texts you the lead details instantly
5. You never miss a customer call again

Pricing: {PRODUCT_PRICE} (no long-term contract)

Want to see it in action? I can do a quick demo.
Or if you're ready to get started, here are the payment options:

- PayPal: {PAYPAL_EMAIL}
- USDT (BEP20): {CRYPTO_USDT}

Let me know!
{WHATSAPP_LINE}
{BUSINESS_NAME}""",

    "interested": f"""Thanks for your interest!

The AI voice assistant is simple:
- It answers your phone 24/7
- Talks to customers in perfect English
- Books appointments to your calendar
- Texts you the details

You never miss a call, even when you're on a job or it's 2 AM.

Pricing: {PRODUCT_PRICE}

Want me to set it up for you? Here's how to pay:
- PayPal: {PAYPAL_EMAIL}
- USDT (BEP20): {CRYPTO_USDT}

Or if you have questions, just ask!
{WHATSAPP_LINE}
{BUSINESS_NAME}""",

    "how_much": f"""Here's the pricing:

Setup (one-time): $500 — I configure the AI for your business
Monthly: $200 — includes all calls, maintenance, and support

No long-term contract. Cancel anytime.

What the AI does:
- Answers every call 24/7
- Books appointments to your calendar
- Qualifies leads (asks about the problem, budget, urgency)
- Texts you the details instantly
- Follows up with customers by SMS

Ready to start? Pay here:
- PayPal: {PAYPAL_EMAIL}
- USDT (BEP20): {CRYPTO_USDT}

{WHATSAPP_LINE}
{BUSINESS_NAME}""",

    "how_works": f"""Here's how it works:

1. Customer calls your business number
2. AI answers instantly: "Hi, thanks for calling [your business]!"
3. AI asks what they need (leak, appointment, quote, etc.)
4. AI books the appointment in your calendar
5. You get a text with: customer name, phone, the problem, the time
6. You just show up — the AI handled everything else

It works 24/7, even when you're sleeping or on a job.

Setup takes 1-2 days. Pricing: {PRODUCT_PRICE}

Want to get started? Pay here:
- PayPal: {PAYPAL_EMAIL}
- USDT (BEP20): {CRYPTO_USDT}

{WHATSAPP_LINE}
{BUSINESS_NAME}""",

    "not_now": """No problem at all!

I'll check back in a few weeks to see if anything has changed.

If you ever need help with missed calls or booking appointments,
just reply to this email.

Have a great week!
{WHATSAPP_LINE}
{BUSINESS_NAME}""",

    "stop": """No problem — I've removed you from my list.

You won't hear from me again.

Best,
{WHATSAPP_LINE}
{BUSINESS_NAME}""",

    "question": f"""Great question!

The AI voice assistant can:
- Answer calls 24/7 in perfect English
- Book appointments directly to your calendar
- Answer common questions (hours, pricing, services, area)
- Qualify leads (asks about the problem and urgency)
- Send you the lead details by text
- Follow up with customers by SMS

Pricing: {PRODUCT_PRICE} (no long-term contract)

What specific questions do you have? I'm happy to explain more.

{WHATSAPP_LINE}
{BUSINESS_NAME}""",

    "demo": f"""I'd love to show you a demo!

Here's what I can do:

Option 1 — Phone demo:
If you give me your phone number, I'll have the AI call you
so you can hear exactly how it sounds. Takes 2 minutes.

Option 2 — See a sample conversation:
Here's what the AI sounds like when a customer calls:

AI: "Hi, thanks for calling! How can I help you today?"
Customer: "I have a leak under my sink, can someone come out?"
AI: "I'm sorry to hear that! I can get someone there today.
     What's your address?"
Customer: "123 Main Street."
AI: "Got it. I have 2 PM available today. Does that work?"
Customer: "Yes, perfect."
AI: "Great! Booked for 2 PM. Our plumber will text you when
     they're on the way. What's your name and number?"

Want the phone demo? Just send me your number.
Or ready to start? Pay here:
- PayPal: {PAYPAL_EMAIL}
- USDT (BEP20): {CRYPTO_USDT}

{WHATSAPP_LINE}
{BUSINESS_NAME}""",

    # === LEAD OFFER RESPONSES ===

    "lead_yes": f"""Great! Here's how to get the customer's contact info:

1. Pay the $25 lead fee:
   - PayPal: {PAYPAL_LEAD_LINK}
   - Crypto (BEP20): {CRYPTO_USDT or "0x27e16d0df86a051e1b14c0f5b90db76d74fd0704"}

2. Reply with your payment confirmation

3. I'll send you the customer's name, phone number, and email immediately

The customer is actively looking for someone right now, so the faster you pay, the faster you can call them and win the job.

{WHATSAPP_LINE}
ProConnect Hub""",

    "lead_which": """Here are the customer leads I have right now:

1. San Antonio, TX — needs plumbing work (asking for plumber recommendation)
2. Chicago, IL — dishwasher water backing up, needs plumber
3. Chicago, IL — lead service line replacement needed
4. Huntington, WV — plumbing redone under sink and dishwasher
5. Portland, OR — garbage disposal problem
6. Raleigh, NC — looking for electrician
7. Carmel, IN — whole home re-wire (aluminum wiring)
8. Dallas, TX — roof replacement (1960s duplex)
9. Frisco, TX — roofing company recommendation
10. Chicago, IL — apartment hunting (renter)
11. Chicago, IL — first-time apartment hunter (renter)

Each lead is $25. Tell me which one(s) you want and I'll send you the payment link.

{WHATSAPP_LINE}
ProConnect Hub""",

    "lead_price": f"""The lead fee is $25 per customer.

You get:
- Customer's full name
- Customer's phone number
- Customer's email
- What they need done
- Their location

Pay per lead — no subscription, no commitment.
Only pay for leads you want.

Pay here:
- PayPal: {PAYPAL_LEAD_LINK}
- Crypto (BEP20): {CRYPTO_USDT or "0x27e16d0df86a051e1b14c0f5b90db76d74fd0704"}

Which lead would you like?

ProConnect Hub""",

    "lead_how": """Here's how it works:

1. I search the internet (Reddit, forums, Craigslist) for people who are actively asking for service recommendations
2. When I find someone who needs a plumber/electrician/roofer, I match them with a business like yours
3. I email you the lead — you decide if you want it
4. If yes, you pay $25 and I send you the customer's contact info
5. You call the customer and quote the job

The customers are real people who posted online saying "I need a plumber" — they're ready to hire someone.

No subscription. No commitment. Pay only for leads you want.

Want a lead? Just say "yes" and I'll send you the payment link.

ProConnect Hub""",
}


def detect_intent(message):
    """Detect what the business is asking based on their reply."""
    msg = message.lower().strip()

    # Lead offer specific intents
    if any(w in msg for w in ["i want the lead", "i'll take the lead", "send me the lead", "send the customer", "i want this lead", "give me the lead", "yes i want", "send me their", "send me the contact"]):
        return "lead_yes"
    if any(w in msg for w in ["which lead", "what lead", "what customer", "which customer", "what leads do you have", "what leads"]):
        return "lead_which"
    if "lead" in msg and any(w in msg for w in ["how much", "price", "cost", "fee"]):
        return "lead_price"
    if "lead" in msg and any(w in msg for w in ["how does this work", "how work", "how do you", "where did you", "how did you find"]):
        return "lead_how"

    if any(w in msg for w in ["unsubscribe", "stop", "remove", "don't", "do not"]):
        return "stop"
    if any(w in msg for w in ["not now", "not interested", "maybe later", "not ready"]):
        return "not_now"
    if any(w in msg for w in ["how much", "price", "cost", "pricing", "how much is"]):
        return "how_much"
    if any(w in msg for w in ["how does it work", "how work", "what does it do", "how this work", "explain"]):
        return "how_works"
    if any(w in msg for w in ["demo", "show me", "see it", "hear it", "sample"]):
        return "demo"
    if any(w in msg for w in ["question", "what about", "can it", "does it", "will it"]):
        return "question"
    if any(w in msg for w in ["yes", "interested", "sure", "ok", "okay", "sounds good", "tell me more"]):
        return "interested"
    if any(w in msg for w in ["no", "nope", "pass", "decline"]):
        return "not_now"

    return "question"  # Default to answering questions


def generate_response(business_reply, business_name=""):
    """Generate the perfect response to a business reply."""
    intent = detect_intent(business_reply)
    response = RESPONSES.get(intent, RESPONSES["question"])

    if business_name:
        response = f"Hi {business_name},\n\n" + response

    return intent, response


def main():
    print("=" * 60)
    print("  💬 REPLY HANDLER")
    print("  Handle business replies WITHOUT speaking English")
    print("=" * 60)
    print()
    print("Paste the business's reply below.")
    print("Press ENTER twice when done (or type 'quit' to exit):")
    print()

    while True:
        lines = []
        empty_count = 0
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line.strip() == "":
                empty_count += 1
                if empty_count >= 2:
                    break
                lines.append("")
            else:
                empty_count = 0
                lines.append(line)

        reply = "\n".join(lines).strip()

        if reply.lower() in ("quit", "exit", "q"):
            break
        if not reply:
            print("No message entered. Try again or type 'quit'.")
            continue

        intent, response = generate_response(reply)

        print()
        print("=" * 60)
        print(f"  📋 DETECTED INTENT: {intent.upper()}")
        print("=" * 60)
        print()
        print("  📧 SUGGESTED RESPONSE (copy and send this):")
        print("-" * 60)
        print()
        print(response)
        print()
        print("-" * 60)
        print()
        print("  ↑ Copy everything above and send it as your reply")
        print()
        print("Paste another reply, or type 'quit' to exit.")
        print()


if __name__ == "__main__":
    main()
