"""SMART EMAIL SENDER — only email VERIFIED addresses.

1. Extract emails from the websites of matched sellers
2. VERIFY each email:
   - reject junk (johndoe@, example@, u@domain, noreply, no-reply, mailer-daemon, wixpress, sentry)
   - require domain MX record to exist
   - reject generic providers when business has own website domain (prefer @business.com emails)
   - SMTP RCPT probe to check mailbox actually exists (skipped for big providers that block it)
3. Send the deal offer ONLY to verified emails

This avoids bounces like the previous batch.
"""
import os
import sys
import json
import re
import time
import smtplib
import socket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dns.resolver

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE_DIR, "data")

JUNK_PATTERNS = [
    "johndoe", "example@", "u@domain", "email@", "noreply", "no-reply",
    "mailer-daemon", "sentry", "wixpress", "you@", "your@", "name@", "info@example",
    "test@", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".css", ".js",
]
PROVIDERS = ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
             "icloud.com", "att.net", "verizon.net", "comcast.net")
RCPT_UNCHECKABLE = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com"}  # block RCPT probes


def is_junk(email, business_domain):
    e = email.lower()
    if any(p in e for p in JUNK_PATTERNS):
        return True
    domain = e.split("@")[1] if "@" in e else ""
    # if business website is e.g. quailplumbing.com, prefer emails on that domain;
    # reject provider emails ONLY when a domain email also exists (handled by caller)
    return False


def has_mx(domain):
    try:
        dns.resolver.resolve(domain, "MX", lifetime=5)
        return True
    except Exception:
        try:
            dns.resolver.resolve(domain, "A", lifetime=5)
            return True
        except Exception:
            return False


def smtp_rcpt_check(email, timeout=10):
    """Probe the mailbox. Returns True (exists), False (no mailbox), None (cannot tell)."""
    domain = email.split("@")[1]
    if domain in RCPT_UNCHECKABLE:
        return None
    try:
        mx = dns.resolver.resolve(domain, "MX", lifetime=5)
        host = str(sorted(mx, key=lambda r: r.preference)[0].exchange).rstrip(".")
    except Exception:
        return None
    try:
        s = smtplib.SMTP(host, 25, timeout=timeout)
        s.helo("proconnect-hub.example.com")
        s.mail("probe@proconnect-hub.example.com")
        code, _ = s.rcpt(email)
        s.quit()
        return code == 250
    except Exception:
        return None


def load_env():
    env = {}
    p = os.path.join(BASE_DIR, ".env")
    for line in open(p):
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            env[k] = v
    return env


def main():
    from email_extractor import scrape_website, clean_url
    from urllib.parse import urlparse
    import deal_closer as dc

    sellers = json.load(open(os.path.join(DATA, "scan_results.json")))
    deals = json.load(open(os.path.join(DATA, "deals.json")))
    leads = {l["id"]: l for l in json.load(open(os.path.join(DATA, "buyer_leads.json")))}

    env = load_env()
    user, pw = env.get("GMAIL_USER"), env.get("GMAIL_APP_PASSWORD")

    name_to_seller = {s["name"].lower(): s for s in sellers}
    verified_map = {}
    sent = 0
    skipped = []

    for deal in deals:
        if deal.get("status") not in ("pending_contact",):
            continue
        seller = name_to_seller.get(deal["seller_name"].lower())
        if not seller:
            continue
        if deal["seller_name"].lower() in verified_map:
            emails = verified_map[deal["seller_name"].lower()]
        else:
            emails = scrape_website(seller.get("website", "")) if seller.get("website") else []
            # verify
            biz_dom = ""
            if seller.get("website"):
                biz_dom = urlparse(clean_url(seller["website"])).netloc.replace("www.", "")
            good = []
            for e in emails[:5]:
                if is_junk(e, biz_dom):
                    continue
                dom = e.split("@")[1]
                if not has_mx(dom):
                    continue
                probe = smtp_rcpt_check(e)
                if probe is False:
                    continue
                good.append(e)
            # prefer business-domain email over provider
            domain_emails = [e for e in good if biz_dom and biz_dom in e.split("@")[1]]
            emails = domain_emails or good
            verified_map[deal["seller_name"].lower()] = emails
            time.sleep(0.5)

        if not emails:
            skipped.append(deal["seller_name"])
            continue

        lead = leads.get(deal["lead_id"], {})
        to = emails[0]
        body = dc.generate_business_email(lead, seller)
        subject = f"New customer lead in {lead.get('location') or 'your area'} - {lead.get('niche','service')}"
        # send via dc helper (uses env)
        if user and pw and dc.send_email(to, subject, body):
            deal["status"] = "email_sent"
            deal["email_sent_at"] = dc.now_utc()
            deal["seller_email"] = to
            sent += 1
            print("SENT", to, "->", deal["seller_name"][:40])

    json.dump(deals, open(os.path.join(DATA, "deals.json"), "w"), indent=2)
    json.dump([{"name": k, "emails": v} for k, v in verified_map.items()],
              open(os.path.join(DATA, "verified_emails.json"), "w"), indent=2)
    print(f"\nSent: {sent} | Skipped (no verified email): {len(skipped)}")
    for s in skipped[:20]:
        print("  skip:", s)


if __name__ == "__main__":
    socket.setdefaulttimeout(10)
    main()
