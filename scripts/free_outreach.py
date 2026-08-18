"""
FREE OUTREACH TOOL
==================
Finds customers for FREE using methods that cost $0:
1. Email outreach (legal cold email with opt-out)
2. Contact form submission (business websites)
3. Social media DM templates (you post manually)
4. Classified ad templates (Craigslist, Gumtree, etc.)
5. WhatsApp/Telegram outreach templates

NO ADS NEEDED. All these methods are free.

LEGAL NOTE:
- Cold EMAIL is legal in US (CAN-SPAM) and most countries IF:
  - You include a real physical address
  - You include an unsubscribe link
  - You don't deceive the recipient
- Cold CALLS need prior consent (TCPA) - we do NOT auto-call
- We generate emails and templates, but YOU review and send them

USAGE:
  python3 scripts/free_outreach.py --generate     (generate outreach for all leads)
  python3 scripts/free_outreach.py --email        (generate emails only)
  python3 scripts/free_outreach.py --social       (generate social media posts)
  python3 scripts/free_outreach.py --classifieds  (generate classified ads)
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lead_finder import load_found_leads

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

BUSINESS_NAME = os.getenv("BUSINESS_NAME", "Our Company")
PRODUCT_NAME = os.getenv("PRODUCT_NAME", "our services")
PRODUCT_PRICE = os.getenv("PRODUCT_PRICE", "")
PRODUCT_DESCRIPTION = os.getenv("PRODUCT_DESCRIPTION", "")
PAYPAL_EMAIL = os.getenv("PAYPAL_EMAIL", "")
CRYPTO_USDT = os.getenv("CRYPTO_USDT_ADDRESS", "")
YOUR_NAME = os.getenv("YOUR_NAME", "")
YOUR_EMAIL = os.getenv("BUSINESS_EMAIL", "")

OUTREACH_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "outreach",
)


def ensure_dir():
    os.makedirs(OUTREACH_DIR, exist_ok=True)


def generate_cold_email(lead):
    """Generate a personalized cold email for a lead."""
    lead_name = lead.get("name", "the owner")
    first_line = f"Hi {lead_name},"

    email = f"""{first_line}

I found your business online and noticed you might benefit from {PRODUCT_NAME}.

{PRODUCT_DESCRIPTION}

Here's what makes us different:
- We focus on real results, not empty promises
- Simple pricing: {PRODUCT_PRICE}
- No long-term contracts

Would you be open to a quick chat this week? Reply with "yes" and I'll send details.

Best regards,
{YOUR_NAME or BUSINESS_NAME}
{YOUR_EMAIL}

---
To stop receiving emails, reply with "UNSUBSCRIBE".
"""
    return email


def generate_contact_form_message(lead):
    """Generate a message for business website contact forms."""
    msg = f"""Hello,

I'm reaching out because I believe {lead.get('name', 'your business')} could benefit from {PRODUCT_NAME}.

{PRODUCT_DESCRIPTION}

Pricing: {PRODUCT_PRICE}

If you're interested, please reply to this message or email me at {YOUR_EMAIL}.

Thank you,
{YOUR_NAME or BUSINESS_NAME}
"""
    return msg


def generate_social_media_post(lead=None):
    """Generate a social media post to attract customers."""
    posts = [
        f"""🚀 Need {PRODUCT_NAME}?

{PRODUCT_DESCRIPTION}

✅ Affordable: {PRODUCT_PRICE}
✅ Fast results
✅ No long contracts

DM me to get started!
#{BUSINESS_NAME.replace(' ', '')} #SmallBusiness #Growth""",
        f"""Struggling with your business growth? 📈

I help businesses like yours with {PRODUCT_NAME}.

{PRODUCT_DESCRIPTION}

Pricing: {PRODUCT_PRICE}

DM me "INFO" and I'll send you the details.""",
        f"""Looking for reliable {PRODUCT_NAME}? 🔍

At {BUSINESS_NAME}, we deliver real results.

{PRODUCT_DESCRIPTION}

Price: {PRODUCT_PRICE}

Message me to learn more! 📩""",
    ]
    return posts


def generate_classified_ad():
    """Generate a classified ad for Craigslist, Gumtree, OLX, Facebook Marketplace."""
    ad = f"""TITLE: Professional {PRODUCT_NAME} - Affordable & Reliable

{PRODUCT_DESCRIPTION}

✅ Price: {PRODUCT_PRICE}
✅ Fast turnaround
✅ Satisfaction guaranteed
✅ No hidden fees

I'm {YOUR_NAME or BUSINESS_NAME}, and I help businesses get real results.

CONTACT:
- Email: {YOUR_EMAIL}
- PayPal: {PAYPAL_EMAIL}
"""
    if CRYPTO_USDT:
        ad += f"- Crypto (USDT/BEP20): {CRYPTO_USDT}\n"
    ad += "\nReply to this ad or contact me directly. Serious inquiries only."
    return ad


def generate_whatsapp_message(lead=None):
    """Generate a WhatsApp/Telegram message for direct outreach."""
    name = lead.get("name", "there") if lead else "there"
    return f"""Hi {name}! 👋

I'm {YOUR_NAME or BUSINESS_NAME}. I found your business and thought you might need {PRODUCT_NAME}.

{PRODUCT_DESCRIPTION}

Price: {PRODUCT_PRICE}

If interested, reply here. If not, just ignore this message. Thanks!"""


def generate_all_outreach():
    """Generate all types of outreach for all leads."""
    ensure_dir()
    leads = load_found_leads()

    if not leads:
        logger.error("No leads found. Run lead_finder.py first!")
        return

    emails = []
    forms = []
    whatsapp = []
    social_posts = generate_social_media_post()
    classified = generate_classified_ad()

    for lead in leads:
        emails.append({
            "lead": lead["name"],
            "email": lead.get("email", "no email found"),
            "subject": f"Quick question about {lead['name']}",
            "body": generate_cold_email(lead),
        })
        forms.append({
            "lead": lead["name"],
            "website": lead.get("website", "no website"),
            "message": generate_contact_form_message(lead),
        })
        whatsapp.append({
            "lead": lead["name"],
            "phone": lead.get("phone", ""),
            "message": generate_whatsapp_message(lead),
        })

    # Save everything
    with open(os.path.join(OUTREACH_DIR, "emails.json"), "w") as f:
        json.dump(emails, f, indent=2)

    with open(os.path.join(OUTREACH_DIR, "contact_forms.json"), "w") as f:
        json.dump(forms, f, indent=2)

    with open(os.path.join(OUTREACH_DIR, "whatsapp_messages.json"), "w") as f:
        json.dump(whatsapp, f, indent=2)

    with open(os.path.join(OUTREACH_DIR, "social_posts.txt"), "w") as f:
        for i, post in enumerate(social_posts, 1):
            f.write(f"=== POST {i} ===\n{post}\n\n")

    with open(os.path.join(OUTREACH_DIR, "classified_ad.txt"), "w") as f:
        f.write(classified)

    logger.info(f"Generated outreach for {len(leads)} leads:")
    logger.info(f"  - {len(emails)} emails → data/outreach/emails.json")
    logger.info(f"  - {len(forms)} contact form messages → data/outreach/contact_forms.json")
    logger.info(f"  - {len(whatsapp)} WhatsApp messages → data/outreach/whatsapp_messages.json")
    logger.info(f"  - {len(social_posts)} social media posts → data/outreach/social_posts.txt")
    logger.info(f"  - 1 classified ad → data/outreach/classified_ad.txt")


def show_outreach(kind="all"):
    """Display the generated outreach content."""
    ensure_dir()

    if kind in ("all", "email"):
        path = os.path.join(OUTREACH_DIR, "emails.json")
        if os.path.exists(path):
            with open(path) as f:
                emails = json.load(f)
            print("\n" + "=" * 50)
            print(f"  EMAILS ({len(emails)} ready to send)")
            print("=" * 50)
            for e in emails[:3]:
                print(f"\nTo: {e['lead']} ({e['email']})")
                print(f"Subject: {e['subject']}")
                print(e["body"])
                print("-" * 40)
            if len(emails) > 3:
                print(f"... and {len(emails) - 3} more in data/outreach/emails.json")

    if kind in ("all", "social"):
        path = os.path.join(OUTREACH_DIR, "social_posts.txt")
        if os.path.exists(path):
            with open(path) as f:
                print("\n" + "=" * 50)
                print("  SOCIAL MEDIA POSTS")
                print("=" * 50)
                print(f.read())

    if kind in ("all", "classifieds"):
        path = os.path.join(OUTREACH_DIR, "classified_ad.txt")
        if os.path.exists(path):
            with open(path) as f:
                print("\n" + "=" * 50)
                print("  CLASSIFIED AD")
                print("=" * 50)
                print(f.read())

    if kind in ("all", "whatsapp"):
        path = os.path.join(OUTREACH_DIR, "whatsapp_messages.json")
        if os.path.exists(path):
            with open(path) as f:
                msgs = json.load(f)
            print("\n" + "=" * 50)
            print(f"  WHATSAPP/TELEGRAM MESSAGES ({len(msgs)})")
            print("=" * 50)
            for m in msgs[:2]:
                print(f"\nTo: {m['lead']} ({m.get('phone', 'no phone')})")
                print(m["message"])
                print("-" * 40)


def main():
    parser = argparse.ArgumentParser(description="Free Customer Outreach Tool")
    parser.add_argument("--generate", action="store_true", help="Generate outreach for all leads")
    parser.add_argument("--email", action="store_true", help="Show emails only")
    parser.add_argument("--social", action="store_true", help="Show social media posts only")
    parser.add_argument("--classifieds", action="store_true", help="Show classified ad only")
    args = parser.parse_args()

    print("=" * 50)
    print("  FREE OUTREACH TOOL")
    print("  Find customers for $0 - no ads needed")
    print("=" * 50)

    if args.generate:
        generate_all_outreach()
        show_outreach("all")
    elif args.email:
        show_outreach("email")
    elif args.social:
        show_outreach("social")
    elif args.classifieds:
        show_outreach("classifieds")
    else:
        print("\nUSAGE:")
        print("  python3 scripts/free_outreach.py --generate     Generate all outreach")
        print("  python3 scripts/free_outreach.py --email        Show emails")
        print("  python3 scripts/free_outreach.py --social       Show social posts")
        print("  python3 scripts/free_outreach.py --classifieds  Show classified ad")
        print()
        print("FREE CHANNELS:")
        print("  1. Email outreach (legal with unsubscribe)")
        print("  2. Website contact forms")
        print("  3. Social media posts (Facebook, Instagram, LinkedIn)")
        print("  4. Classified ads (Craigslist, OLX, Facebook Marketplace)")
        print("  5. WhatsApp/Telegram DMs")
        print()
        print("Step 1: Find leads:   python3 scripts/lead_finder.py")
        print("Step 2: Generate:     python3 scripts/free_outreach.py --generate")


if __name__ == "__main__":
    main()
