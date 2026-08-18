"""
GMAIL READER (IMAP)
===================
Reads replies from businesses automatically using Gmail IMAP.

Only returns REAL business replies — filters out newsletters,
notifications, marketing emails, and old junk.

FREE: Gmail IMAP is free, no API needed.
Works with the same App Password you already set up.

USAGE:
  python3 scripts/gmail_reader.py              (check for replies)
  python3 scripts/gmail_reader.py --days 30    (check last 30 days)
"""
import os
import sys
import imaplib
import email
import logging
import argparse
from email.header import decode_header
from datetime import datetime as dt, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")


def is_configured():
    return bool(GMAIL_USER and GMAIL_APP_PASSWORD)


def decode_email_header(header_value):
    if not header_value:
        return ""
    decoded_parts = decode_header(header_value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or "utf-8", errors="replace"))
            except Exception:
                result.append(part.decode("utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def get_email_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in disposition:
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break
                except Exception:
                    pass
        if not body:
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
                        import re
                        body = re.sub(r"<[^>]+>", "", body)
                        break
                    except Exception:
                        pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
        except Exception:
            body = str(msg.get_payload())
    return body.strip()


# Senders that are NEVER real business replies
SKIP_SENDERS = [
    "noreply", "no-reply", "mailer-daemon", "postmaster",
    "notification", "donotreply", "newsletter", "updates@",
    "facebookmail", "googlemail", "google.com", "youtube.com",
    "twitter.com", "linkedin.com", "instagram.com",
    "amazon", "apple.com", "microsoft.com",
    "marketing", "promo", "offers@", "deals@",
    "notify", "alert@", "automated", "bounce", "spam",
    "email.mspy", "jooble", "whatclinic", "lovecointoken",
    "programminghub", "afrisight", "verify@",
    "team@", "hello@email", "subscribe@", "security@facebook",
    "members@", "admin@", "welcome@", "mail@",
]

# Subject keywords that indicate notifications/newsletters
SKIP_SUBJECTS = [
    "newsletter", "weekly digest", "your weekly", "daily summary",
    "verify your email", "confirm your", "welcome to", "activation",
    "password reset", "security alert", "new login", "new message from",
    "job alert", "new jobs", "your subscription", "unsubscribe",
    "delivery status", "undeliverable", "mail delivery failed",
    "verification code", "one-time code", "your code",
    "update to your", "security notice", "please complete",
    "partons", "bienvenue", "veuillez",
]


def is_real_reply(from_email, subject, body):
    """Check if an email is a real business reply (not a newsletter)."""
    from_lower = from_email.lower()
    subject_lower = subject.lower()

    # Skip our own emails
    if GMAIL_USER.lower() in from_lower:
        return False

    # Skip known newsletter/notification senders
    if any(s in from_lower for s in SKIP_SENDERS):
        return False

    # Skip by subject keywords
    if any(s in subject_lower for s in SKIP_SUBJECTS):
        return False

    # Only process emails that look like REAL replies:
    # - Subject starts with "Re:" (it's a reply)
    # - OR body mentions our product keywords
    is_reply = subject_lower.startswith("re:")
    mentions_product = False
    if body:
        body_lower = body.lower()
        mentions_product = any(w in body_lower for w in [
            "ai assistant", "ai voice", "missed call", "after-hours",
            "voice assistant", "24/7", "booking appointments",
            "ai pro assist", "after hours calls", "$500", "$200",
        ])

    if not is_reply and not mentions_product:
        return False

    # Skip newsletters (too many links)
    if body.count("http") > 10:
        return False

    # Skip auto-replies (too short)
    if len(body.strip()) < 20:
        return False

    return True


def read_replies(mark_as_read=True, folder="INBOX", days_back=7):
    """
    Read unread replies from Gmail — only REAL business replies.

    Returns: [{from_email, from_name, subject, body, date, message_id}]
    """
    if not is_configured():
        logger.error("Gmail not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD in .env")
        return []

    replies = []

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select(folder)

        since_date = (dt.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(UNSEEN SINCE {since_date})')
        if status != "OK":
            logger.info("No unread emails found")
            mail.logout()
            return []

        email_ids = messages[0].split()
        logger.info(f"Found {len(email_ids)} unread email(s) from last {days_back} days")

        for eid in email_ids:
            try:
                status, msg_data = mail.fetch(eid, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                from_header = msg.get("From", "")
                from_email = ""
                from_name = ""

                if "<" in from_header:
                    from_name = from_header.split("<")[0].strip().strip('"')
                    from_email = from_header.split("<")[1].split(">")[0].strip()
                else:
                    from_email = from_header.strip()

                subject = decode_email_header(msg.get("Subject", ""))
                body = get_email_body(msg)
                date = msg.get("Date", "")
                message_id = msg.get("Message-ID", "")

                if not is_real_reply(from_email, subject, body):
                    continue

                reply = {
                    "from_email": from_email,
                    "from_name": from_name,
                    "subject": subject,
                    "body": body[:5000],
                    "date": date,
                    "message_id": message_id,
                }
                replies.append(reply)

                logger.info(f"  📬 REAL REPLY from: {from_email}")
                logger.info(f"     Subject: {subject[:50]}")
                logger.info(f"     Preview: {body[:80]}...")

            except Exception as e:
                logger.error(f"  Error reading email: {e}")

        if mark_as_read and email_ids:
            for eid in email_ids:
                mail.store(eid, "+FLAGS", "\\Seen")

        mail.logout()
    except Exception as e:
        logger.error(f"IMAP connection failed: {e}")

    return replies


def main():
    parser = argparse.ArgumentParser(description="Gmail Reader")
    parser.add_argument("--days", type=int, default=7, help="Days to look back")
    parser.add_argument("--no-mark", action="store_true", help="Don't mark as read")
    args = parser.parse_args()

    print("=" * 60)
    print("  📬 GMAIL READER")
    print("=" * 60)

    if not is_configured():
        print("Gmail not configured!")
        return

    replies = read_replies(mark_as_read=not args.no_mark, days_back=args.days)

    if not replies:
        print(f"\nNo real business replies found in last {args.days} days.")
        print("Businesses may not have replied yet. Check again tomorrow.")
    else:
        print(f"\nFound {len(replies)} real reply/replies:\n")
        for i, r in enumerate(replies, 1):
            print(f"--- Reply {i} ---")
            print(f"From: {r['from_name']} <{r['from_email']}>")
            print(f"Date: {r['date']}")
            print(f"Subject: {r['subject']}")
            print(f"Body: {r['body'][:300]}...")
            print()


if __name__ == "__main__":
    main()
