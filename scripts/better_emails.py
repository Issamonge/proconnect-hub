"""
HIGH-CONVERTING EMAIL GENERATOR
================================
Creates personalized, high-converting cold emails for each lead.

These emails are designed to get responses:
- Personalized to the business name
- Focused on THEIR problem (missed calls = lost money)
- Specific numbers ($ lost per missed call)
- Short, skimmable, mobile-friendly
- Clear single call-to-action
- Legal (CAN-SPAM: unsubscribe + real address)

USAGE:
  python3 scripts/better_emails.py              (generate for all leads)
  python3 scripts/better_emails.py --top 25     (top 25 hottest only)
  python3 scripts/better_emails.py --niche plumber   (plumbers only)
"""
import os
import sys
import json
import logging
import argparse
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

BUSINESS_NAME = os.getenv("BUSINESS_NAME", "AI Pro Assist")
YOUR_EMAIL = os.getenv("BUSINESS_EMAIL", "")
PAYPAL_EMAIL = os.getenv("PAYPAL_EMAIL", "")
LANDING_PAGE_URL = os.getenv("LANDING_PAGE_URL", "")
WHATSAPP_LINK = os.getenv("WHATSAPP_LINK", "")
BUSINESS_PHONE = os.getenv("BUSINESS_PHONE", "")

SCAN_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "scan_results.json",
)
OUTPUT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "outreach",
    "better_emails.json",
)

# Niche-specific email angles
NICHE_ANGLES = {
    "plumber": {
        "problem": "When a customer has a burst pipe at 2 AM and you don't answer, they call the next plumber. That's a $500-$2,000 job lost.",
        "benefit": "An AI that answers every call, books emergency visits, and texts you the details — even at 3 AM.",
        "subject": "Question about your after-hours calls",
    },
    "electrician": {
        "problem": "Emergency electrical calls don't wait. If you're on a job and miss the call, that customer is gone.",
        "benefit": "An AI assistant that answers 24/7, screens emergencies, and books the job — so you never lose one.",
        "subject": "Never miss an emergency call again",
    },
    "dentist": {
        "problem": "New patients call to book. If they hit voicemail, 70% call the next dentist.",
        "benefit": "An AI that answers instantly, books appointments directly into your calendar, and fills your chairs.",
        "subject": "Filling your open appointment slots",
    },
    "restaurant": {
        "problem": "Every missed call could be a reservation or catering order — both lost revenue.",
        "benefit": "An AI that answers every call, takes reservations, and answers menu/hours questions instantly.",
        "subject": "Catching your missed reservation calls",
    },
    "hairdresser": {
        "problem": "Clients call to book while you're with another client. Missed call = missed booking.",
        "benefit": "An AI that books appointments 24/7 and texts you the details between clients.",
        "subject": "Booking appointments while you're busy",
    },
    "real_estate": {
        "problem": "In real estate, speed wins. The agent who responds first gets the client.",
        "benefit": "An AI that answers instantly, qualifies buyers/sellers, and books showings on your calendar.",
        "subject": "Responding to leads before other agents",
    },
    "car_repair": {
        "problem": "Customers call for quotes and bookings. Miss the call and they call the next shop.",
        "benefit": "An AI that answers every call, gives basic quotes, and books service appointments.",
        "subject": "Catching your missed service calls",
    },
    "veterinary": {
        "problem": "Pet owners call with urgent questions. If you can't answer, they worry and go elsewhere.",
        "benefit": "An AI that answers 24/7, triages emergencies, and books appointments.",
        "subject": "Handling after-hours pet emergencies",
    },
    "lawyer": {
        "problem": "New case leads call once. If they reach voicemail, they call the next firm.",
        "benefit": "An AI that answers instantly, does initial intake, and books consultations on your calendar.",
        "subject": "Catching your new case leads",
    },
    "gym": {
        "problem": "Prospects call about memberships and classes. Missed calls = lost sign-ups.",
        "benefit": "An AI that answers 24/7, answers membership questions, and books tours/trials.",
        "subject": "Turning missed calls into memberships",
    },
    "roofing": {
        "problem": "When a storm hits, homeowners call multiple roofers. The first one to answer gets the job — worth $5,000-$20,000+.",
        "benefit": "An AI that answers every call 24/7, books inspections, and texts you the lead instantly.",
        "subject": "Catching storm-damage calls you're missing",
    },
    "real_estate": {
        "problem": "In real estate, speed wins. The agent who responds first gets the client.",
        "benefit": "An AI that answers instantly, qualifies buyers/sellers, and books showings on your calendar.",
        "subject": "Responding to leads before other agents",
    },
}


def clean_name(name):
    """Clean up lead names (remove HTML entities, directory prefixes, page titles)."""
    import html
    name = html.unescape(name)
    # Remove common page title prefixes
    for prefix in [
        "The Real Yellow Pages", "Top 10 Best", "Best ", "The Best 10",
        "Contact ", "CONTACT ", "Contact Us", "Contact the ", "Find ",
    ]:
        if name.startswith(prefix):
            name = name[len(prefix):].strip().lstrip("-|: ")
    # Take the actual business name (before | or - or : separators)
    for sep in [" | ", " - ", " |", "- ", " | ", " – "]:
        if sep in name:
            name = name.split(sep)[0].strip()
    name = name.strip().rstrip(",|:-").strip()
    if not name or len(name) < 3:
        name = "there"
    return name[:50]


def extract_business_name(name):
    """Extract a clean business name from a search result title."""
    name = clean_name(name)
    # If what's left looks like a sentence fragment, try to get a cleaner name
    words = name.split()
    # If first word is a generic word, the title is probably not a business name
    generic_first_words = {
        "contact", "the", "top", "best", "find", "about",
        "trusted", "affordable", "professional", "licensed",
        "welcome", "home", "services", "plumbing",
    }
    if words and words[0].lower().strip(",") in generic_first_words:
        # Try to find a proper noun (capitalized word that's not generic)
        for w in words[1:]:
            if w[0].isupper() and w.lower().strip(",.") not in generic_first_words:
                # Found a potential business name — return everything from that word
                idx = name.index(w)
                return name[idx:].strip()
    return name


def generate_better_email(lead):
    """Generate a high-converting personalized email."""
    niche = lead.get("scan_niche", lead.get("niche", ""))
    angle = NICHE_ANGLES.get(niche, NICHE_ANGLES["plumber"])

    raw_name = lead.get("name", "your business")
    name = extract_business_name(raw_name)
    city = lead.get("scan_city", lead.get("location", ""))

    subject = angle["subject"]

    # Greeting: use business name if it looks like one, otherwise "Hi there"
    greeting_name = name
    # If the name is just one generic word, use "there"
    if len(name.split()) <= 1 and name.lower() in ("contact", "about", "home", "services"):
        greeting_name = "there"

    email_body = f"""Hi {greeting_name},

I'll be quick — I found {name} online and noticed something:

{angle['problem']}

Here's what I do: {angle['benefit']}

It's an AI voice assistant that answers your phone 24/7, talks to customers in perfect English, and books appointments directly into your calendar. You get a text with every lead.

No more missed calls. No more lost jobs.

Setup: $500 (one-time)
Monthly: $200 (includes all calls + maintenance)

{f'See how it works: {LANDING_PAGE_URL}' if LANDING_PAGE_URL else ''}

Worth a 5-minute chat this week?

Reply "yes" and I'll send you a demo.
{f'Or message me on WhatsApp: {WHATSAPP_LINK}' if WHATSAPP_LINK else ''}

Best,
{BUSINESS_NAME}
{YOUR_EMAIL}
{f'WhatsApp: {WHATSAPP_LINK}' if WHATSAPP_LINK else ''}

---
Reply "UNSUBSCRIBE" to stop receiving emails.
"""
    return {"subject": subject, "body": email_body}


def main():
    parser = argparse.ArgumentParser(description="Generate High-Converting Emails")
    parser.add_argument("--top", type=int, help="Only generate for top N hottest leads")
    parser.add_argument("--niche", type=str, help="Only generate for specific niche")
    args = parser.parse_args()

    print("=" * 60)
    print("  HIGH-CONVERTING EMAIL GENERATOR")
    print("=" * 60)

    if not os.path.exists(SCAN_FILE):
        logger.error("No scan results found. Run hot_lead_scanner.py first!")
        return

    with open(SCAN_FILE) as f:
        leads = json.load(f)

    # Filter
    if args.niche:
        leads = [l for l in leads if l.get("scan_niche") == args.niche]
    if args.top:
        leads = leads[:args.top]

    logger.info(f"Generating high-converting emails for {len(leads)} leads...")

    emails = []
    for lead in leads:
        email = generate_better_email(lead)
        emails.append({
            "lead": clean_name(lead.get("name", "")),
            "niche": lead.get("scan_niche", ""),
            "city": lead.get("scan_city", ""),
            "hotness": lead.get("hotness_score", 0),
            "subject": email["subject"],
            "body": email["body"],
        })

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(emails, f, indent=2)

    logger.info(f"Saved {len(emails)} emails to {OUTPUT_FILE}")

    # Show samples
    print()
    print("=" * 60)
    print("  📧 SAMPLE EMAILS (showing first 3)")
    print("=" * 60)

    for i, email in enumerate(emails[:3], 1):
        print(f"\n--- EMAIL {i} ---")
        print(f"To: {email['lead']} ({email['niche']} in {email['city']})")
        print(f"Hotness: {email['hotness']}/100")
        print(f"Subject: {email['subject']}")
        print()
        print(email["body"])
        print("-" * 60)

    if len(emails) > 3:
        print(f"\n... and {len(emails) - 3} more in data/outreach/better_emails.json")
        print()
        print("TO SEND:")
        print("  1. Open data/outreach/better_emails.json")
        print("  2. Copy each email's subject + body")
        print("  3. Send from your Gmail to the business")
        print("  4. When they reply 'yes' → tell me, I'll help you respond")


if __name__ == "__main__":
    main()
