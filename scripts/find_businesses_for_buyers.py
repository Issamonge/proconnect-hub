"""Find businesses in the cities where our buyer leads live,
and add them to scan_results.json."""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rebuild_businesses import ddg_search, parse_business

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_FILE = os.path.join(BASE_DIR, "data", "scan_results.json")
LEADS_FILE = os.path.join(BASE_DIR, "data", "buyer_leads.json")

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

leads = json.load(open(LEADS_FILE))
sellers = json.load(open(SCAN_FILE))
existing = {(s["name"].lower(), s["niche"], s["location"]) for s in sellers}

# niche + city pairs from buyer leads
pairs = set()
for l in leads:
    niche = l.get("niche") or "real_estate"
    loc = l.get("location", "").strip()
    if loc:
        pairs.add((niche, loc))
print(f"Searching {len(pairs)} niche/city pairs...")

added = 0
for niche, city in sorted(pairs):
    term = NICHES.get(niche, niche)
    try:
        results = ddg_search(f"{term} {city} phone contact")
        parsed = [b for b in (parse_business(r, niche, city) for r in results) if b]
        for b in parsed:
            key = (b["name"].lower(), b["niche"], b["location"])
            if key not in existing:
                existing.add(key)
                sellers.append(b)
                added += 1
        print(f"{niche} @ {city}: +{len(parsed)}")
    except Exception as e:
        print(f"{niche} @ {city}: FAILED {e}")
    time.sleep(2)

json.dump(sellers, open(SCAN_FILE, "w"), indent=2)
print(f"\nAdded {added} new businesses. Total: {len(sellers)}")
