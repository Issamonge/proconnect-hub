"""
BUYER & RENTER FINDER
=====================
Searches the internet for real people who need services or property.
No ads needed — finds people who are actively posting "I need a plumber" etc.

Searches:
- Reddit (r/Plumbing, r/HomeImprovement, r/DIY, r/Renters, r/Apartments)
- Craigslist (services wanted, housing wanted)
- Forums and Q&A sites
- Twitter/X posts
- Facebook group posts (via search)

When it finds a match:
1. Saves the buyer/renter lead
2. Matches with businesses from our database
3. Generates a reply message to connect them
4. Notifies you by email

USAGE:
  python3 scripts/buyer_finder.py                    # Search for all buyer/renter posts
  python3 scripts/buyer_finder.py --niche plumber    # Search only for plumbing needs
  python3 scripts/buyer_finder.py --renters          # Search for people needing property
  python3 scripts/buyer_finder.py --stats            # Show found leads stats
"""
import os
import sys
import json
import logging
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
BUYER_LEADS_FILE = os.path.join(DATA_DIR, "buyer_leads.json")
SCAN_FILE = os.path.join(DATA_DIR, "scan_results.json")

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD", "")
BUSINESS_EMAIL = os.getenv("BUSINESS_EMAIL", GMAIL_USER)

# Tavily API for internet search (free tier available)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Search queries to find people who need services
BUYER_SEARCH_QUERIES = {
    "plumber": [
        'site:reddit.com "need a plumber" OR "looking for plumber" OR "plumber recommendation"',
        '"need a plumber" "near me" -ad 2024 OR 2025 OR 2026',
        'site:craigslist.org "plumbing" "wanted" OR "need"',
        '"plumbing emergency" "need help" -ad',
    ],
    "electrician": [
        'site:reddit.com "need an electrician" OR "looking for electrician"',
        '"need an electrician" "near me" -ad 2024 OR 2025 OR 2026',
        'site:craigslist.org "electrical" "wanted" OR "need"',
        '"electrical work" "need help" -ad',
    ],
    "roofing": [
        'site:reddit.com "need a roofer" OR "roof repair" "looking for"',
        '"need a roofer" "near me" -ad 2024 OR 2025 OR 2026',
        '"roof leak" "need help" -ad',
        'site:craigslist.org "roofing" "wanted"',
    ],
    "car_repair": [
        'site:reddit.com "need a mechanic" OR "car repair" "looking for"',
        '"need a mechanic" "near me" -ad 2024 OR 2025 OR 2026',
        '"car broke down" "need help" -ad',
    ],
    "dentist": [
        'site:reddit.com "need a dentist" OR "looking for dentist"',
        '"need a dentist" "near me" -ad',
        '"dental emergency" "need help" -ad',
    ],
    "lawyer": [
        'site:reddit.com "need a lawyer" OR "looking for attorney" "recommendation"',
        '"need a lawyer" "near me" -ad',
        '"legal advice" "need help" -ad',
    ],
    "veterinary": [
        'site:reddit.com "need a vet" OR "looking for vet" "emergency"',
        '"need a vet" "near me" -ad',
        '"pet emergency" "need help" -ad',
    ],
    "real_estate": [
        'site:reddit.com "looking for realtor" OR "need a real estate agent"',
        '"need a realtor" "near me" -ad',
    ],
}

RENTER_SEARCH_QUERIES = [
    'site:reddit.com "looking for apartment" OR "need to rent" OR "apartment hunting" 2024 OR 2025 OR 2026',
    'site:reddit.com/r/Apartments "looking for" OR "need" "apartment"',
    'site:craigslist.org "housing wanted" OR "apartment wanted"',
    '"looking for apartment" "near me" -ad 2024 OR 2025 OR 2026',
    '"need to rent" "house" OR "apartment" -ad',
    '"looking for room" "rent" -ad 2024 OR 2025 OR 2026',
    'site:reddit.com/r/Renters "looking for" OR "need"',
]


def load_buyer_leads():
    if not os.path.exists(BUYER_LEADS_FILE):
        return []
    with open(BUYER_LEADS_FILE) as f:
        return json.load(f)


def save_buyer_leads(leads):
    with open(BUYER_LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2)


def load_sellers():
    if not os.path.exists(SCAN_FILE):
        return []
    with open(SCAN_FILE) as f:
        return json.load(f)


def find_matching_sellers(niche, city=""):
    """Find businesses that match the buyer's service need."""
    sellers = load_sellers()
    matches = [s for s in sellers if s.get("niche") == niche and s.get("phone","").strip()]
    if not matches:
        matches = [s for s in sellers if s.get("niche") == niche]
    return matches[:3]


def tavily_search(query, max_results=10):
    """Search the internet using Tavily API."""
    if not TAVILY_API_KEY:
        logger.warning("No TAVILY_API_KEY set. Using Google search as fallback.")
        return google_fallback_search(query)

    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            "include_raw_content": False,
            "search_depth": "advanced",
        }
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", "")[:500],
                    "score": item.get("score", 0),
                })
            return results
        else:
            logger.error(f"Tavily search failed: {r.status_code}")
            return []
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []


def google_fallback_search(query):
    """Fallback: use DuckDuckGo HTML search (no API key needed)."""
    try:
        r = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        import re
        results = []
        # Parse DuckDuckGo HTML results
        titles = re.findall(r'<a rel="nofollow" class="result__a"[^>]*>(.*?)</a>', r.text)
        urls = re.findall(r'<a rel="nofollow" class="result__a"[^>]*href="(.*?)"', r.text)
        snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)

        for i in range(min(len(titles), len(urls), max_results := 10)):
            title = re.sub(r'<[^>]+>', '', titles[i]) if i < len(titles) else ""
            url_raw = urls[i] if i < len(urls) else ""
            content = re.sub(r'<[^>]+>', '', snippets[i])[:500] if i < len(snippets) else ""
            # DuckDuckGo wraps URLs in a redirect
            if "uddg=" in url_raw:
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(url_raw)
                params = parse_qs(parsed.query)
                url_clean = params.get("uddg", [url_raw])[0]
            else:
                url_clean = url_raw
            results.append({"title": title, "url": url_clean, "content": content, "score": 0.5})
        return results
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
        return []


def extract_location_from_text(text):
    """Try to extract a city/location from search result text."""
    import re
    # Look for patterns like "in Chicago", "Chicago, IL", etc.
    patterns = [
        r'in ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2})',
        r'in ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'near ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2})',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1)
    return ""


def is_real_request(title, content):
    """Check if a search result looks like a real person asking for help (not an ad)."""
    text = (title + " " + content).lower()
    # Positive signals — someone asking for help
    asking_signals = ["need", "looking for", "recommend", "anyone know", "help", "urgent", "emergency",
                      "can't find", "searching for", "who does", "where can i"]
    # Negative signals — ads or business listings
    ad_signals = ["call now", "free quote", "book online", "schedule now", "discount",
                  "$ off", "best price", "hire us", "our services", "contact us today",
                  "visit our", "follow us", "subscribe"]

    has_asking = any(s in text for s in asking_signals)
    has_ad = any(s in text for s in ad_signals)

    return has_asking and not has_ad


def search_buyers(niche=None):
    """Search the internet for people who need services."""
    all_found = []
    niches = [niche] if niche else list(BUYER_SEARCH_QUERIES.keys())

    for n in niches:
        queries = BUYER_SEARCH_QUERIES.get(n, [])
        logger.info(f"\n🔍 Searching for {n} buyers...")

        for query in queries:
            results = tavily_search(query, max_results=5)
            for r in results:
                if is_real_request(r["title"], r["content"]):
                    location = extract_location_from_text(r["content"])
                    lead = {
                        "id": f"BUYER-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{len(all_found)}",
                        "type": "buyer",
                        "niche": n,
                        "title": r["title"],
                        "url": r["url"],
                        "description": r["content"],
                        "location": location,
                        "found_at": datetime.utcnow().isoformat(),
                        "status": "found",
                        "matched_sellers": [],
                    }

                    # Match with sellers from our database
                    matches = find_matching_sellers(n, location)
                    if matches:
                        lead["matched_sellers"] = [
                            {"name": m.get("name",""), "phone": m.get("phone",""), "location": m.get("location","")}
                            for m in matches
                        ]
                        lead["status"] = "matched"

                    all_found.append(lead)
                    status = "✅ MATCHED" if matches else "📍 FOUND"
                    logger.info(f"  {status}: {r['title'][:60]}")
                    if location:
                        logger.info(f"     Location: {location}")
                    if matches:
                        logger.info(f"     Matched with {len(matches)} businesses")

    # Deduplicate by URL
    seen_urls = set()
    unique = []
    for l in all_found:
        if l["url"] not in seen_urls:
            seen_urls.add(l["url"])
            unique.append(l)

    return unique


def search_renters():
    """Search the internet for people looking for property to rent/buy."""
    all_found = []

    for query in RENTER_SEARCH_QUERIES:
        logger.info(f"\n🏠 Searching for renters...")
        results = tavily_search(query, max_results=5)
        for r in results:
            if is_real_request(r["title"], r["content"]):
                location = extract_location_from_text(r["content"])
                lead = {
                    "id": f"RENTER-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{len(all_found)}",
                    "type": "renter",
                    "title": r["title"],
                    "url": r["url"],
                    "description": r["content"],
                    "location": location,
                    "found_at": datetime.utcnow().isoformat(),
                    "status": "found",
                    "matched_sellers": [],
                }

                # Match with real estate businesses
                matches = find_matching_sellers("real_estate", location)
                if matches:
                    lead["matched_sellers"] = [
                        {"name": m.get("name",""), "phone": m.get("phone",""), "location": m.get("location","")}
                        for m in matches
                    ]
                    lead["status"] = "matched"

                all_found.append(lead)
                status = "✅ MATCHED" if matches else "📍 FOUND"
                logger.info(f"  {status}: {r['title'][:60]}")

    seen_urls = set()
    unique = []
    for l in all_found:
        if l["url"] not in seen_urls:
            seen_urls.add(l["url"])
            unique.append(l)
    return unique


def generate_reply_message(lead):
    """Generate a reply message to post/comment to the buyer."""
    niche = lead.get("niche", "service")
    matches = lead.get("matched_sellers", [])

    if not matches:
        return f"""Hi! I saw you're looking for a {niche.replace('_',' ')}. I'd be happy to help connect you with someone in your area. What city are you in? I have a network of verified local pros who can give you a free quote."""

    seller_list = "\n".join([
        f"  • {m['name']} ({m.get('location','')}) — {m.get('phone','')}"
        for m in matches
    ])

    return f"""Hi! I saw you're looking for a {niche.replace('_',' ')}. I run ProConnect Hub — we connect people with verified local pros.

Here are 3 {niche.replace('_',' ')}s who can help:

{seller_list}

They can all give you free quotes. Hope this helps! Feel free to DM me if you need anything else."""


def get_stats():
    leads = load_buyer_leads()
    buyers = [l for l in leads if l.get("type") == "buyer"]
    renters = [l for l in leads if l.get("type") == "renter"]
    matched = [l for l in leads if l.get("status") == "matched"]
    return {
        "total": len(leads),
        "buyers": len(buyers),
        "renters": len(renters),
        "matched": len(matched),
        "unmatched": len(leads) - len(matched),
    }


def main():
    parser = argparse.ArgumentParser(description="Find buyers and renters on the internet")
    parser.add_argument("--niche", type=str, help="Search for specific niche only")
    parser.add_argument("--renters", action="store_true", help="Search for renters only")
    parser.add_argument("--stats", action="store_true", help="Show stats only")
    parser.add_argument("--all", action="store_true", help="Search for both buyers and renters")
    args = parser.parse_args()

    print("=" * 60)
    print("  PROCONNECT HUB — BUYER & RENTER FINDER")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    if args.stats:
        s = get_stats()
        print(f"\n  Total leads found: {s['total']}")
        print(f"  Buyers: {s['buyers']}")
        print(f"  Renters: {s['renters']}")
        print(f"  Matched with sellers: {s['matched']}")
        print(f"  Unmatched: {s['unmatched']}")
        return

    # Load existing leads
    existing = load_buyer_leads()
    existing_urls = {l.get("url","") for l in existing}

    new_leads = []

    if args.renters:
        new_leads = search_renters()
    elif args.all:
        new_leads = search_buyers() + search_renters()
    else:
        new_leads = search_buyers(niche=args.niche)

    # Filter out already-found leads
    truly_new = [l for l in new_leads if l.get("url","") not in existing_urls]

    # Combine and save
    all_leads = existing + truly_new
    save_buyer_leads(all_leads)

    print(f"\n{'='*60}")
    print(f"  SEARCH COMPLETE")
    print(f"{'='*60}")
    print(f"  Found {len(new_leads)} leads ({len(truly_new)} new)")
    print(f"  Matched with businesses: {len([l for l in new_leads if l.get('status')=='matched'])}")
    print(f"  Total in database: {len(all_leads)}")

    # Show matched leads with reply messages
    matched = [l for l in truly_new if l.get("status") == "matched"]
    if matched:
        print(f"\n{'='*60}")
        print(f"  MATCHED LEADS — Ready to contact")
        print(f"{'='*60}")
        for l in matched[:5]:
            print(f"\n  📌 {l['title'][:70]}")
            print(f"  🔗 {l['url']}")
            print(f"  📍 Location: {l.get('location','unknown')}")
            print(f"  🤝 Matched with {len(l['matched_sellers'])} businesses")
            print(f"\n  💬 REPLY MESSAGE:")
            print(f"  {'-'*50}")
            msg = generate_reply_message(l)
            for line in msg.split('\n'):
                print(f"  {line}")
            print(f"  {'-'*50}")


if __name__ == "__main__":
    main()
