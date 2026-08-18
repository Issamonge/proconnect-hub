#!/usr/bin/env python3
"""
AGGRESSIVE LEAD GENERATOR
=========================
Finds 200+ leads across 10+ cities and 5+ niches.
Uses DuckDuckGo web search (free, no API key needed).

Usage:
  python3 scripts/agg_lead_finder.py           # find 200+ leads
  python3 scripts/agg_lead_finder.py --max 500 # find up to 500
"""
import os
import sys
import json
import time
import logging
import requests
import re
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
RESULTS_FILE = os.path.join(DATA_DIR, "scan_results.json")

# 12 cities across US, UK, Canada, Australia
CITIES = [
    "Chicago, IL", "Houston, TX", "Phoenix, AZ", "Philadelphia, PA",
    "San Antonio, TX", "San Diego, CA", "Dallas, TX", "San Jose, CA",
    "Austin, TX", "Jacksonville, FL", "Columbus, OH", "Charlotte, NC",
    "Manchester, UK", "Birmingham, UK", "Glasgow, UK", "Leeds, UK",
    "Montreal, Canada", "Vancouver, Canada", "Calgary, Canada", "Ottawa, Canada",
    "Sydney, Australia", "Melbourne, Australia", "Brisbane, Australia",
]

# 7 niches
NICHES = ["plumber", "electrician", "dentist", "lawyer", "real estate agent", "car repair", "veterinary"]

DIRECTORY_DOMAINS = [
    "yellowpages.com", "yelp.com", "angi.com", "homeadvisor.com",
    "facebook.com", "linkedin.com", "superpages.com", "manta.com",
    "bbb.org", "thumbtack.com", "foursquare.com", "mapquest.com",
    "wikipedia.org", "reddit.com", "indeed.com", "glassdoor.com",
    "craigslist.org", "youtube.com", "tiktok.com", "instagram.com",
    "twitter.com", "x.com", "pinterest.com", "trustpilot.com",
    "tripadvisor.com", "opencorporates.com", "companieshouse.gov.uk",
]

def search_ddg(query, max_results=20):
    """Search DuckDuckGo HTML and extract business names + URLs."""
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    results = []
    try:
        resp = requests.post(url, data={"q": query}, headers=headers, timeout=20)
        text = resp.text
        names = re.findall(r'class="result__a"[^>]*>([^<]+)</a>', text)
        urls_raw = re.findall(r'class="result__url"[^>]*>([^<]+)</a>', text)
        for name, web in zip(names, urls_raw):
            name = name.strip()
            web = web.strip()
            if not name or not web:
                continue
            if any(d in web.lower() for d in DIRECTORY_DOMAINS):
                continue
            results.append({"name": name, "website": web})
            if len(results) >= max_results:
                break
    except Exception as e:
        logger.error(f"Search failed for '{query}': {e}")
    return results

def load_existing():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            return json.load(f)
    return []

def save_leads(leads):
    with open(RESULTS_FILE, "w") as f:
        json.dump(leads, f, indent=2)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=300, help="Max total leads to find")
    args = parser.parse_args()

    existing = load_existing()
    logger.info(f"Starting aggressive lead generation. Existing leads: {len(existing)}")
    logger.info(f"Target: {args.max} new leads across {len(CITIES)} cities x {len(NICHES)} niches")

    seen_keys = set()
    for l in existing:
        key = (l.get("name", "").lower().strip(), l.get("scan_city", "").lower().strip())
        seen_keys.add(key)

    new_leads = []
    total_checked = 0

    for city in CITIES:
        for niche in NICHES:
            if len(new_leads) >= args.max:
                break

            queries = [
                f'{niche} {city} contact email -site:yellowpages.com -site:yelp.com',
                f'"{niche}" "{city}" contact us phone',
                f'{niche} {city} website contact',
            ]

            for query in queries:
                if len(new_leads) >= args.max:
                    break
                results = search_ddg(query, max_results=10)
                for r in results:
                    key = (r["name"].lower().strip(), city.lower().strip())
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    new_leads.append({
                        "name": r["name"],
                        "phone": "",
                        "email": "",
                        "website": r["website"],
                        "address": "",
                        "niche": niche,
                        "scan_niche": niche,
                        "scan_city": city,
                        "location": city,
                        "source": "web_search_aggressive",
                        "found_at": datetime.now().isoformat(),
                        "status": "new",
                    })
                    total_checked += 1
                time.sleep(1)  # Be polite

            # Save incrementally after each niche
            all_leads = existing + new_leads
            save_leads(all_leads)

            logger.info(f"  {city} / {niche}: {len(new_leads)} new leads so far")
            time.sleep(0.5)

        if len(new_leads) >= args.max:
            break

    all_leads = existing + new_leads
    save_leads(all_leads)

    logger.info(f"DONE! Found {len(new_leads)} new leads (total now: {len(all_leads)})")
    logger.info(f"Results saved to: {RESULTS_FILE}")

    # Summary
    from collections import Counter
    city_counts = Counter(l.get("scan_city", "?") for l in all_leads)
    niche_counts = Counter(l.get("scan_niche", l.get("niche", "?")) for l in all_leads)
    logger.info(f"Cities: {dict(city_counts)}")
    logger.info(f"Niches: {dict(niche_counts)}")

if __name__ == "__main__":
    main()
