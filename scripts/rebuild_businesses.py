"""Rebuild scan_results.json (business database) by scraping DuckDuckGo results.

Overpass API is unreachable from this sandbox, so we parse business names
and phone numbers from search result snippets instead.
"""
import os
import re
import json
import time
import html
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_FILE = os.path.join(BASE_DIR, "data", "scan_results.json")

NICHES = {
    "plumber": "plumber",
    "electrician": "electrician",
    "roofing": "roofing contractor",
    "car_repair": "auto repair shop",
    "dentist": "dentist",
    "lawyer": "lawyer attorney",
    "veterinary": "veterinarian vet clinic",
    "real_estate": "real estate agent realtor",
}
CITIES = ["Chicago, IL", "Houston, TX", "Phoenix, AZ", "Dallas, TX", "Denver, CO"]

DIRECTORY_DOMAINS = ["yelp", "yellowpages", "angi", "thumbtack", "homeadvisor",
                     "bbb.org", "expertise.com", "yell.com", "facebook",
                     "mapquest", "superpages", "porch.com", "houzz", "nextdoor",
                     "reddit", "wikipedia", "forbes", "bankrate", "nerdwallet"]

PHONE_RE = re.compile(r'\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}')


def clean(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s)).strip()


def ddg_search(query):
    r = requests.get("https://html.duckduckgo.com/html/",
                     params={"q": query},
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', r.text)
    links = re.findall(r'class="result__a"[^>]*href="(.*?)"', r.text)
    snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)
    out = []
    for t, l, s in zip(titles, links, snips):
        out.append({"title": clean(t), "url": html.unescape(l), "snippet": clean(s)})
    return out


def parse_business(result, niche, city):
    url = result["url"].lower()
    if any(d in url for d in DIRECTORY_DOMAINS):
        return None
    title = result["title"]
    # Name is usually the part before | or - or ::
    name = re.split(r'\s[\|\-–—:]{1,2}\s', title)[0].strip()
    name = re.sub(r'(?i)^(contact|about|home|services)\b[\s\|\-]*', '', name).strip()
    if len(name) < 4 or len(name) > 60:
        return None
    if any(w in name.lower() for w in ["top ", "best ", "find ", "near me", "how to"]):
        return None
    phones = PHONE_RE.findall(result["snippet"] + " " + title)
    phone = phones[0] if phones else ""
    return {
        "name": name,
        "phone": phone,
        "email": "",
        "website": result["url"],
        "address": "",
        "niche": niche,
        "location": city,
        "source": "duckduckgo",
        "found_at": datetime.now().isoformat(),
        "status": "new",
    }


def main():
    all_businesses = []
    for niche, term in NICHES.items():
        for city in CITIES:
            query = f'{term} {city} phone contact'
            try:
                results = ddg_search(query)
                parsed = [b for b in (parse_business(r, niche, city) for r in results) if b]
                with_phone = [b for b in parsed if b["phone"]]
                print(f"{niche} @ {city}: {len(parsed)} ({len(with_phone)} with phone)")
                all_businesses.extend(parsed)
            except Exception as e:
                print(f"{niche} @ {city}: FAILED {e}")
            time.sleep(2)

    seen = set()
    unique = []
    for b in all_businesses:
        key = (b["name"].lower(), b["niche"], b["location"])
        if key not in seen:
            seen.add(key)
            unique.append(b)

    os.makedirs(os.path.dirname(SCAN_FILE), exist_ok=True)
    with open(SCAN_FILE, "w") as f:
        json.dump(unique, f, indent=2)
    print(f"\nTotal unique businesses saved: {len(unique)}")
    print(f"With phone numbers: {len([b for b in unique if b['phone']])}")


if __name__ == "__main__":
    main()
