"""
CRAIGSLIST BUYER FINDER
=======================
Searches Craigslist "services wanted" and "housing wanted" posts.
No API key needed — Craigslist has free RSS feeds and public HTML.

Finds people who:
- Need plumbing, electrical, roofing, etc. (services wanted)
- Need apartments/houses to rent (housing wanted)

When it finds a match:
1. Saves the buyer lead
2. Matches with businesses from our database
3. Generates contact message
4. Notifies you by email

USAGE:
  python3 scripts/craigslist_finder.py              # Search all cities
  python3 scripts/craigslist_finder.py --stats      # Show stats
"""
import os
import sys
import json
import logging
import argparse
import re
from datetime import datetime, timezone
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
BUYER_LEADS_FILE = os.path.join(DATA_DIR, "buyer_leads.json")
SCAN_FILE = os.path.join(DATA_DIR, "scan_results.json")

try:
    import requests
except ImportError:
    logger.error("requests not installed")
    sys.exit(1)

# Craigslist cities we cover (based on our business database)
CRAIGSLIST_CITIES = {
    "seattle": "https://seattle.craigslist.org",
    "chicago": "https://chicago.craigslist.org",
    "dallas": "https://dallas.craigslist.org",
    "denver": "https://denver.craigslist.org",
    "boston": "https://boston.craigslist.org",
    "houston": "https://houston.craigslist.org",
    "jacksonville": "https://jacksonville.craigslist.org",
    "columbus": "https://columbus.craigslist.org",
    "sanantonio": "https://sanantonio.craigslist.org",
    "portland": "https://portland.craigslist.org",
    "raleigh": "https://raleigh.craigslist.org",
    "indianapolis": "https://indianapolis.craigslist.org",
}

# Services to search for on Craigslist
SERVICE_KEYWORDS = {
    "plumber": ["plumber", "plumbing", "pipe", "leak", "drain", "water heater", "faucet", "toilet"],
    "electrician": ["electrician", "electrical", "wiring", "outlet", "panel", "breaker", "light"],
    "roofing": ["roof", "roofing", "gutter", "shingle", "leak roof"],
    "car_repair": ["mechanic", "auto repair", "car repair", "brake", "engine", "transmission"],
    "dentist": ["dentist", "dental", "teeth", "tooth"],
    "lawyer": ["lawyer", "attorney", "legal", "divorce", "bankruptcy"],
    "veterinary": ["vet", "veterinary", "pet", "animal clinic"],
    "real_estate": ["real estate", "realtor", "property manager", "rental"],
}

# Housing wanted keywords
HOUSING_KEYWORDS = ["apartment", "house", "rent", "studio", "bedroom", "move in"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def now_utc():
    return datetime.now(timezone.utc).isoformat()


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


def find_matching_sellers(niche, location=""):
    sellers = load_sellers()
    matches = [s for s in sellers if s.get("niche") == niche and s.get("phone", "").strip()]
    if not matches:
        matches = [s for s in sellers if s.get("niche") == niche]

    if location:
        buyer_city = location.split(",")[0].strip().lower()
        same_city = [s for s in matches if buyer_city in s.get("location", "").lower()]
        if same_city:
            return same_city[:3]
    return matches[:3]


def search_craigslist_city(city_key, city_url, category="sss"):
    """Search Craigslist for a given city. category 'sss' = services, 'hhh' = housing wanted."""
    results = []
    for niche, keywords in SERVICE_KEYWORDS.items():
        for keyword in keywords[:3]:  # Top 3 keywords per niche
            try:
                # Search services wanted
                search_url = f"{city_url}/search/sss"
                params = {"query": keyword, "sort": "date", "format": "rss"}
                r = requests.get(search_url, params=params, headers=HEADERS, timeout=10)
                if r.status_code == 200:
                    posts = parse_craigslist_results(r.text, city_key, niche, keyword)
                    results.extend(posts)
            except Exception as e:
                logger.debug(f"  Search error for {city_key}/{keyword}: {e}")

    return results


def parse_craigslist_results(html, city, niche, keyword):
    """Parse Craigslist RSS/HTML results to extract post info."""
    posts = []
    # RSS item pattern
    items = re.findall(r"<item>(.*?)</item>", html, re.DOTALL)
    for item in items:
        title_match = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item) or re.search(r"<title>(.*?)</title>", item)
        link_match = re.search(r"<link>(.*?)</link>", item)
        desc_match = re.search(r"<description><!\[CDATA\[(.*?)\]\]></description>", item, re.DOTALL) or re.search(r"<description>(.*?)</description>", item, re.DOTALL)

        if title_match and link_match:
            title = title_match.group(1).strip()
            link = link_match.group(1).strip()
            desc = desc_match.group(1)[:300] if desc_match else ""

            # Filter: only "wanted" or "need" posts
            title_lower = title.lower()
            if any(w in title_lower for w in ["wanted", "need", "looking for", "seeking", "need a", "need an"]):
                posts.append({
                    "title": title,
                    "url": link,
                    "description": re.sub(r"<[^>]+>", "", desc).strip()[:200],
                    "city": city,
                    "niche": niche,
                    "keyword": keyword,
                })
    return posts


def search_housing_wanted(city_key, city_url):
    """Search Craigslist housing wanted section."""
    results = []
    try:
        search_url = f"{city_url}/search/hhh"
        params = {"query": "apartment wanted", "sort": "date"}
        r = requests.get(search_url, params=params, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            posts = parse_craigslist_results(r.text, city_key, "real_estate", "apartment wanted")
            results.extend(posts)
    except Exception as e:
        logger.debug(f"  Housing search error for {city_key}: {e}")
    return results


def search_all_craigslist():
    """Search Craigslist in all our cities."""
    all_found = []
    for city_key, city_url in CRAIGSLIST_CITIES.items():
        logger.info(f"Searching Craigslist {city_key}...")
        service_posts = search_craigslist_city(city_key, city_url)
        housing_posts = search_housing_wanted(city_key, city_url)
        all_found.extend(service_posts + housing_posts)

        if service_posts or housing_posts:
            logger.info(f"  Found {len(service_posts)} service posts, {len(housing_posts)} housing posts")

    # Deduplicate by URL
    seen = set()
    unique = []
    for p in all_found:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique.append(p)
    return unique


def process_found_posts(posts):
    """Convert found posts into buyer leads and match with sellers."""
    existing = load_buyer_leads()
    existing_urls = {l.get("url", "") for l in existing}
    new_leads = []

    for post in posts:
        if post["url"] in existing_urls:
            continue

        niche = post.get("niche", "")
        city = post.get("city", "")
        matches = find_matching_sellers(niche, city)

        lead = {
            "id": f"CL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{len(new_leads)}",
            "type": "buyer",
            "niche": niche,
            "title": post["title"],
            "url": post["url"],
            "description": post["description"],
            "location": city,
            "source": "craigslist",
            "found_at": now_utc(),
            "status": "matched" if matches else "found",
            "matched_sellers": [
                {"name": m.get("name", ""), "phone": m.get("phone", ""), "location": m.get("location", "")}
                for m in matches
            ],
        }
        new_leads.append(lead)

    all_leads = existing + new_leads
    save_buyer_leads(all_leads)
    return new_leads


def search_other_platforms():
    """Search Quora and other forums for people needing services."""
    all_found = []

    # Use Tavily search if available, else DuckDuckGo
    queries = [
        ('site:quora.com "need a plumber" OR "looking for plumber" 2025 2026', "plumber"),
        ('site:quora.com "need an electrician" OR "looking for electrician" 2025 2026', "electrician"),
        ('site:quora.com "need a roofer" OR "roof repair" 2025 2026', "roofing"),
        ('site:nextdoor.com "need a plumber" OR "plumber recommendation" 2025 2026', "plumber"),
        ('site:angi.com "need" "plumber" OR "electrician" OR "roofer" 2025 2026', "plumber"),
        ('"need a plumber" OR "need an electrician" "near me" -ad 2025 2026', "plumber"),
        ('"looking for" "plumber" OR "electrician" OR "roofer" forum 2025 2026', "plumber"),
    ]

    tavily_key = os.getenv("TAVILY_API_KEY", "")
    for query, niche in queries:
        if tavily_key:
            try:
                r = requests.post("https://api.tavily.com/search", json={
                    "api_key": tavily_key,
                    "query": query,
                    "max_results": 5,
                    "search_depth": "basic",
                }, timeout=20)
                if r.status_code == 200:
                    for item in r.json().get("results", []):
                        title = item.get("title", "")
                        url = item.get("url", "")
                        content = item.get("content", "")[:300]
                        text = (title + " " + content).lower()
                        if any(w in text for w in ["need", "looking for", "recommend", "help", "urgent"]):
                            if not any(w in text for w in ["call now", "free quote", "book online", "hire us", "our services"]):
                                all_found.append({
                                    "title": title,
                                    "url": url,
                                    "description": content,
                                    "niche": niche,
                                    "source": "web_search",
                                })
            except Exception as e:
                logger.debug(f"  Tavily search error: {e}")

    return all_found


def process_web_results(results):
    """Convert web search results into buyer leads."""
    existing = load_buyer_leads()
    existing_urls = {l.get("url", "") for l in existing}
    new_leads = []

    for result in results:
        if result["url"] in existing_urls:
            continue

        niche = result.get("niche", "")
        matches = find_matching_sellers(niche)

        lead = {
            "id": f"WEB-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{len(new_leads)}",
            "type": "buyer",
            "niche": niche,
            "title": result["title"],
            "url": result["url"],
            "description": result["description"],
            "location": "",
            "source": result.get("source", "web_search"),
            "found_at": now_utc(),
            "status": "matched" if matches else "found",
            "matched_sellers": [
                {"name": m.get("name", ""), "phone": m.get("phone", ""), "location": m.get("location", "")}
                for m in matches
            ],
        }
        new_leads.append(lead)

    all_leads = existing + new_leads
    save_buyer_leads(all_leads)
    return new_leads


def get_stats():
    leads = load_buyer_leads()
    buyers = [l for l in leads if l.get("type") == "buyer"]
    renters = [l for l in leads if l.get("type") == "renter"]
    matched = [l for l in leads if l.get("status") == "matched"]
    by_source = {}
    for l in leads:
        src = l.get("source", "reddit")
        by_source[src] = by_source.get(src, 0) + 1
    return {
        "total": len(leads),
        "buyers": len(buyers),
        "renters": len(renters),
        "matched": len(matched),
        "by_source": by_source,
    }


def main():
    parser = argparse.ArgumentParser(description="Find buyers on Craigslist and other platforms")
    parser.add_argument("--stats", action="store_true", help="Show stats only")
    parser.add_argument("--web", action="store_true", help="Search web (Quora, forums) instead of Craigslist")
    args = parser.parse_args()

    print("=" * 60)
    print("  PROCONNECT HUB - BUYER FINDER (Craigslist + Web)")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    if args.stats:
        s = get_stats()
        print(f"\n  Total buyer/renter leads: {s['total']}")
        print(f"  Buyers: {s['buyers']}")
        print(f"  Renters: {s['renters']}")
        print(f"  Matched with businesses: {s['matched']}")
        print(f"\n  By source:")
        for src, count in sorted(s["by_source"].items()):
            print(f"    {src}: {count}")
        return

    if args.web:
        logger.info("Searching the web (Quora, forums, etc.) for buyers...")
        results = search_other_platforms()
        new_leads = process_web_results(results)
        logger.info(f"Found {len(results)} results, {len(new_leads)} new leads added")
    else:
        logger.info("Searching Craigslist for buyers...")
        posts = search_all_craigslist()
        logger.info(f"Found {len(posts)} Craigslist posts")
        new_leads = process_found_posts(posts)
        logger.info(f"Added {len(new_leads)} new buyer leads")

    # Show results
    if new_leads:
        matched = [l for l in new_leads if l.get("status") == "matched"]
        print(f"\n{'='*60}")
        print(f"  NEW LEADS FOUND: {len(new_leads)} ({len(matched)} matched)")
        print(f"{'='*60}")
        for l in new_leads[:10]:
            icon = "🔍" if l["type"] == "buyer" else "🏠"
            m = len(l.get("matched_sellers", []))
            print(f"\n  {icon} {l['title'][:55]}")
            print(f"     Source: {l.get('source', '?')} | 📍 {l.get('location', '?')} | 🤝 {m} businesses")
            if m > 0:
                for s in l["matched_sellers"]:
                    print(f"       → {s['name'][:30]} ({s.get('phone', '')})")


if __name__ == "__main__":
    main()
