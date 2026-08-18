"""
EMAIL EXTRACTOR
===============
Scrapes business websites to find real contact email addresses.

The lead finder finds business names and websites, but we need actual
email addresses to send outreach. This module visits each business's
website and extracts any email addresses found on the page.

METHODS:
1. Visit the website homepage
2. Check common contact pages (/contact, /contact-us, /about)
3. Extract emails from the HTML using regex
4. Clean and validate the emails (no images, no duplicates)

USAGE:
  python3 scripts/email_extractor.py              (extract for all leads with websites)
  python3 scripts/email_extractor.py --limit 20   (only 20 leads)
  python3 scripts/email_extractor.py --update     (update scan_results.json with emails)
"""
import os
import re
import sys
import json
import time
import logging
import argparse
from urllib.parse import urljoin, urlparse
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# Regex to find email addresses in HTML
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

# Emails to ignore (common junk, system emails)
SKIP_EMAILS = {
    "example@", "test@", "sample@", "your@", "email@",
    "domain@", "sentry@", "noreply@", "no-reply@", "wixpress@",
    "godaddy@", "wordpress@", "shopify@", "support@sentry",
    "notifications@", "ingest@", "sentry.io", "example.com",
    "yourdomain@", "myemail@", "placeholder@",
}

# Skip emails from these domains (platform/system emails, not business emails)
SKIP_EMAIL_DOMAINS = [
    "wixpress.com", "sentry.io", "sentry-next.wixpress.com",
    "example.com", "sentry.com", "cloudflare.com",
    "gmail.com+_",  # malformed
]

# Directory sites that don't contain individual business emails
DIRECTORY_DOMAINS = [
    "yellowpages.com", "angi.com", "yelp.com", "superpages.com",
    "plumbersden.com", "homeadvisor.com", "thumbtack.com",
    "bbb.org", "manta.com", "foursquare.com", "mapquest.com",
    "facebook.com", "linkedin.com", "instagram.com", "twitter.com",
    "wikipedia.org", "reddit.com", "pinterest.com", "tiktok.com",
    "youtube.com", "maps.google", "google.com/maps",
    "craigslist.org", "indeed.com", "glassdoor.com",
]

# Query patterns that find individual businesses (not directory pages)
# Format: {site} -{directory} to exclude directories from results
SEARCH_QUERY_SUFFIX = "-site:yellowpages.com -site:yelp.com -site:angi.com -site:homeadvisor.com -site:facebook.com -site:linkedin.com"

# Pages to check on each website
CONTACT_PAGES = ["", "/contact", "/contact-us", "/about", "/about-us", "/team"]

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SCAN_FILE = os.path.join(DATA_DIR, "scan_results.json")
EMAILS_FILE = os.path.join(DATA_DIR, "extracted_emails.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def clean_url(url):
    """Ensure URL has http/https prefix."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url


def extract_emails_from_html(html):
    """Find all email addresses in an HTML string."""
    emails = set()
    for match in EMAIL_REGEX.finditer(html):
        email = match.group().lower().strip(".")
        # Skip junk emails
        if any(s in email for s in SKIP_EMAILS):
            continue
        # Skip platform/system email domains
        domain = email.split("@")[1] if "@" in email else ""
        if any(d in email for d in SKIP_EMAIL_DOMAINS):
            continue
        # Skip emails that are just file names or CSS
        if email.endswith((".png", ".jpg", ".gif", ".css", ".js")):
            continue
        # Must have a real domain with a dot
        if "@" in email and "." in domain:
            emails.add(email)
    return emails


def is_directory_site(url):
    """Check if URL is a directory site (Yellow Pages, Yelp, etc.) — skip these."""
    url_lower = url.lower()
    return any(d in url_lower for d in DIRECTORY_DOMAINS)


def scrape_website(base_url, timeout=10):
    """Visit a website and its contact pages, extract emails."""
    all_emails = set()
    base_url = clean_url(base_url)
    if not base_url:
        return []

    # Skip directory sites — they don't have individual business emails
    if is_directory_site(base_url):
        logger.info(f"  Skipping directory site: {base_url}")
        return []

    parsed = urlparse(base_url)
    if not parsed.netloc:
        return []

    for page in CONTACT_PAGES:
        url = urljoin(base_url, page)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            if resp.status_code == 200:
                emails = extract_emails_from_html(resp.text)
                all_emails.update(emails)
                if emails:
                    logger.info(f"  Found {len(emails)} email(s) on {page or '/'}")
        except Exception:
            pass
        time.sleep(0.5)  # Be polite

    # Prefer emails that look like contact/business emails
    sorted_emails = sorted(all_emails, key=lambda e: (
        0 if any(w in e for w in ["info", "contact", "admin", "office", "hello", "mail"]) else 1,
        e,
    ))

    return sorted_emails


def extract_all_emails(limit=None, update_scan=False):
    """Extract emails for all leads that have websites."""
    if not os.path.exists(SCAN_FILE):
        logger.error("No scan results. Run hot_lead_scanner.py first!")
        return []

    with open(SCAN_FILE) as f:
        leads = json.load(f)

    if limit:
        leads = leads[:limit]

    logger.info(f"Extracting emails for {len(leads)} leads...")

    results = []
    found_count = 0

    for i, lead in enumerate(leads, 1):
        name = lead.get("name", "Unknown")
        website = lead.get("website", "")

        if not website:
            continue

        logger.info(f"[{i}/{len(leads)}] {name[:40]} → {website}")

        emails = scrape_website(website)

        if emails:
            found_count += 1
            lead["extracted_emails"] = emails
            results.append({
                "name": name,
                "niche": lead.get("scan_niche", ""),
                "city": lead.get("scan_city", ""),
                "website": website,
                "emails": emails,
                "hotness": lead.get("hotness_score", 0),
            })
            logger.info(f"  ✅ Found: {', '.join(emails[:3])}")
        else:
            logger.info(f"  ❌ No emails found")

        # Be polite - wait between sites
        time.sleep(1)

    # Save extracted emails
    with open(EMAILS_FILE, "w") as f:
        json.dump(results, f, indent=2)

    # Update scan_results with emails if requested
    if update_scan:
        with open(SCAN_FILE, "w") as f:
            json.dump(leads, f, indent=2)

    logger.info(f"Done! Found emails for {found_count}/{len(leads)} leads")
    logger.info(f"Saved to {EMAILS_FILE}")
    return results


def get_leads_with_emails():
    """Load leads that have extracted emails."""
    if not os.path.exists(EMAILS_FILE):
        return []
    with open(EMAILS_FILE) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Extract emails from business websites")
    parser.add_argument("--limit", type=int, help="Max leads to process")
    parser.add_argument("--update", action="store_true", help="Update scan_results.json with emails")
    args = parser.parse_args()

    print("=" * 60)
    print("  📧 EMAIL EXTRACTOR")
    print("  Scraping business websites for contact emails")
    print("=" * 60)

    results = extract_all_emails(limit=args.limit, update_scan=args.update)

    if results:
        print(f"\n✅ Found emails for {len(results)} businesses:")
        for r in results[:10]:
            print(f"  {r['name'][:40]} → {', '.join(r['emails'][:2])}")
        if len(results) > 10:
            print(f"  ... and {len(results) - 10} more in data/extracted_emails.json")
    else:
        print("\n❌ No emails found. The leads may not have websites with contact emails.")


if __name__ == "__main__":
    main()
