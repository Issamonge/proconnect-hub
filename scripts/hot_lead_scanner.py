"""
HOT LEAD SCANNER
================
Scans MULTIPLE business niches at once, finds leads, and scores them
by "hotness" — how likely they are to buy an AI voice assistant.

HOTNESS SIGNALS (what makes a lead "hot"):
- Has a website but NO phone number shown → needs an AI to catch calls
- Website looks old/simple → needs modernization
- Listed on directories (Yellow Pages, Angi) → actively seeking customers
- No online booking system → needs AI to book appointments
- High competition niche → more pressure to respond fast
- Service business (misses calls = lost revenue) → needs 24/7 answering

USAGE:
  python3 scripts/hot_lead_scanner.py              (scan all niches)
  python3 scripts/hot_lead_scanner.py --limit 10   (10 leads per niche)
  python3 scripts/hot_lead_scanner.py --top 20     (show top 20 hottest)
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lead_finder import find_leads, save_found_leads

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# All the niches to scan — service businesses that lose money from missed calls
NICHES = [
    {"name": "plumber",      "hotness": 95, "reason": "Emergencies = missed calls = lost $500+ jobs"},
    {"name": "electrician",  "hotness": 90, "reason": "Emergency calls, high job value"},
    {"name": "dentist",      "hotness": 85, "reason": "Booking appointments = perfect for AI"},
    {"name": "restaurant",   "hotness": 80, "reason": "Reservations + questions = AI can handle"},
    {"name": "hairdresser",  "hotness": 78, "reason": "Booking appointments, repeat customers"},
    {"name": "real_estate",  "hotness": 75, "reason": "Lead capture is everything in real estate"},
    {"name": "car_repair",   "hotness": 82, "reason": "Service bookings, price questions"},
    {"name": "veterinary",   "hotness": 70, "reason": "Appointments + emergency calls"},
    {"name": "lawyer",       "hotness": 72, "reason": "Lead intake, case screening"},
    {"name": "gym",          "hotness": 65, "reason": "Membership inquiries, class booking"},
]

# Cities to scan (major cities = more businesses)
CITIES = [
    "New York, NY",
    "Los Angeles, CA",
    "Chicago, IL",
    "Houston, TX",
    "Miami, FL",
]

SCAN_RESULTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "scan_results.json",
)


def score_lead(lead, niche_info):
    """
    Score a lead's hotness (0-100).
    Higher = more likely to need an AI voice assistant.
    """
    score = niche_info["hotness"]
    reasons = [niche_info["reason"]]

    name = lead.get("name", "").lower()
    website = lead.get("website", "")
    phone = lead.get("phone", "")
    source = lead.get("source", "")

    # Signals that increase hotness
    if not phone and website:
        score += 10
        reasons.append("Has website but no phone shown → AI can catch calls")
    if "yellow pages" in name or "angi" in name or "yelp" in name:
        score += 5
        reasons.append("Listed on directory → actively seeking customers")
    if not website:
        score += 8
        reasons.append("No website → needs modern solution")
    if "contact" in name or "booking" in name or "appointment" in name:
        score += 5
        reasons.append("Mentions contact/booking → needs automation")

    # Cap at 100
    score = min(score, 100)

    return {
        "score": score,
        "reasons": reasons,
        "niche": niche_info["name"],
        "niche_hotness": niche_info["hotness"],
    }


def scan_all_niches(limit_per_niche=10, cities=None):
    """
    Scan all niches across multiple cities.
    Returns all leads with hotness scores.
    """
    cities = cities or CITIES
    all_leads = []

    total_niches = len(NICHES)
    total_cities = len(cities)
    total_scans = total_niches * total_cities

    logger.info(f"Scanning {total_niches} niches × {total_cities} cities = {total_scans} searches")

    scan_num = 0
    for niche in NICHES:
        for city in cities:
            scan_num += 1
            logger.info(f"[{scan_num}/{total_scans}] {niche['name']} in {city}...")

            try:
                leads = find_leads(niche["name"], city, limit_per_niche)
            except Exception as e:
                logger.error(f"  Failed: {e}")
                leads = []

            for lead in leads:
                lead["scan_city"] = city
                lead["scan_niche"] = niche["name"]
                hotness = score_lead(lead, niche)
                lead["hotness_score"] = hotness["score"]
                lead["hotness_reasons"] = hotness["reasons"]
                lead["scanned_at"] = datetime.now().isoformat()
                all_leads.append(lead)

            logger.info(f"  Found {len(leads)} leads")

    # Sort by hotness score (hottest first)
    all_leads.sort(key=lambda x: x.get("hotness_score", 0), reverse=True)

    # Save results
    os.makedirs(os.path.dirname(SCAN_RESULTS_FILE), exist_ok=True)
    with open(SCAN_RESULTS_FILE, "w") as f:
        json.dump(all_leads, f, indent=2)

    # Also save to found_leads for the outreach tool
    save_found_leads(all_leads)

    logger.info(f"Total leads found: {len(all_leads)}")
    return all_leads


def show_results(leads, top=20):
    """Display the hottest leads."""
    print()
    print("=" * 70)
    print(f"  🔥 HOTTEST LEADS (Top {min(top, len(leads))} of {len(leads)})")
    print("=" * 70)

    # Group by niche
    niche_counts = {}
    for lead in leads:
        n = lead.get("scan_niche", "unknown")
        niche_counts[n] = niche_counts.get(n, 0) + 1

    print()
    print("📊 LEADS BY NICHE:")
    for niche, count in sorted(niche_counts.items(), key=lambda x: x[1], reverse=True):
        n_info = next((n for n in NICHES if n["name"] == niche), None)
        emoji = "🔥" if n_info and n_info["hotness"] >= 85 else "⚡" if n_info and n_info["hotness"] >= 75 else "📍"
        print(f"  {emoji} {niche:15s} → {count} leads (base hotness: {n_info['hotness'] if n_info else '?'})")

    print()
    print("-" * 70)
    print(f"{'#':>3} {'SCORE':>5}  {'NICHE':<14} {'LEAD NAME':<40} {'CITY'}")
    print("-" * 70)

    for i, lead in enumerate(leads[:top], 1):
        score = lead.get("hotness_score", 0)
        niche = lead.get("scan_niche", "?")
        name = lead.get("name", "?")[:38]
        city = lead.get("scan_city", "?")[:15]
        bar = "🔥" if score >= 90 else "⚡" if score >= 80 else "📍" if score >= 70 else "  "
        print(f"{i:>3} {score:>4}  {bar} {niche:<14} {name:<40} {city}")

    print()
    print("=" * 70)
    print("  💡 RECOMMENDATION")
    print("=" * 70)
    best_niche = max(niche_counts, key=niche_counts.get)
    best_niche_info = next((n for n in NICHES if n["name"] == best_niche), None)
    print()
    print(f"  Start with: {best_niche.upper()}")
    if best_niche_info:
        print(f"  Why: {best_niche_info['reason']}")
    print(f"  Leads available: {niche_counts[best_niche]}")
    print()
    print("  Next step: Generate outreach for these leads:")
    print("    python3 scripts/free_outreach.py --generate")


def main():
    parser = argparse.ArgumentParser(description="Hot Lead Scanner")
    parser.add_argument("--limit", type=int, default=10, help="Leads per niche per city")
    parser.add_argument("--top", type=int, default=20, help="Show top N hottest leads")
    parser.add_argument("--cities", nargs="+", help="Override cities to scan")
    args = parser.parse_args()

    print("=" * 70)
    print("  🔥 HOT LEAD SCANNER")
    print("  Scanning multiple niches to find the best opportunities")
    print("=" * 70)
    print()
    print(f"Niches: {', '.join(n['name'] for n in NICHES)}")
    print(f"Cities: {', '.join(args.cities or CITIES)}")
    print()

    leads = scan_all_niches(
        limit_per_niche=args.limit,
        cities=args.cities,
    )

    if leads:
        show_results(leads, top=args.top)
    else:
        print("No leads found. Check your internet connection.")


if __name__ == "__main__":
    main()
