"""
LEAD FINDER
===========
Searches the internet for potential leads automatically.

This module finds businesses/people who might want your product,
then adds them to the database so the AI agent can call them.

DATA SOURCES (free options):
1. Google Places API - local businesses (free tier: 200 requests/month)
2. OpenStreetMap / Overpass API - free, no API key needed
3. Google Maps scraping - find businesses by type and location
4. Apollo.io API - B2B contacts (free tier: 100 leads/month)
5. Hunter.io API - find emails for a domain (free tier: 25 searches/month)

CONFIGURATION:
Set these in your .env file:
  LEAD_SEARCH_NICHE=plumbers         (what type of business to find)
  LEAD_SEARCH_LOCATION=Chicago, IL   (where to find them)
  LEAD_SEARCH_LIMIT=50               (max leads per search)
  GOOGLE_PLACES_API_KEY=             (optional - for Google Places)
  APOLLO_API_KEY=                    (optional - for B2B leads)
"""
import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lead_database import init_db

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "leads.db")
LEADS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "found_leads.json")


def find_leads_overpass(niche, location, limit=50):
    """
    Find local businesses using OpenStreetMap Overpass API.
    FREE - no API key needed.
    """
    logger.info(f"Searching Overpass for '{niche}' in '{location}'...")

    # Map common business types to OSM tags
    niche_tags = {
        "plumber": '["craft"="plumber"]',
        "electrician": '["craft"="electrician"]',
        "restaurant": '["amenity"="restaurant"]',
        "cafe": '["amenity"="cafe"]',
        "barber": '["shop"="hairdresser"]',
        "hairdresser": '["shop"="hairdresser"]',
        "beauty": '["shop"="beauty"]',
        "dentist": '["amenity"="dentist"]',
        "doctor": '["amenity"="doctors"]',
        "lawyer": '["office"="lawyer"]',
        "real_estate": '["office"="estate_agent"]',
        "car_repair": '["shop"="car_repair"]',
        "gym": '["leisure"="fitness_centre"]',
        "bakery": '["shop"="bakery"]',
        "florist": '["shop"="florist"]',
        "jewelry": '["shop"="jewelry"]',
        "furniture": '["shop"="furniture"]',
        "pet_shop": '["shop"="pet"]',
        "pharmacy": '["amenity"="pharmacy"]',
        "veterinary": '["amenity"="veterinary"]',
    }

    # Build the tag filter
    tag = niche_tags.get(niche.lower(), f'["name"~"{niche}",i]')

    # Use a geocoding area - first search for the location
    geocode_url = "https://nominatim.openstreetmap.org/search"
    geo_params = {
        "q": location,
        "format": "json",
        "limit": 1,
    }
    headers = {"User-Agent": "AI-Lead-Finder/1.0"}

    try:
        geo_resp = requests.get(geocode_url, params=geo_params, headers=headers, timeout=15)
        geo_data = geo_resp.json()
        if not geo_data:
            logger.error(f"Location not found: {location}")
            return []
        area_id = geo_data[0]["osm_id"] + 3_600_000_000  # area relation ID
    except Exception as e:
        logger.error(f"Geocoding failed: {e}")
        return []

    # Query Overpass for businesses in that area
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:25];
    area({area_id})->.searchArea;
    (
      node{tag}(area.searchArea);
      way{tag}(area.searchArea);
    );
    out center 50;
    """

    try:
        resp = requests.post(overpass_url, data={"data": query}, timeout=30)
        data = resp.json()
        elements = data.get("elements", [])
        logger.info(f"Found {len(elements)} results from Overpass")
    except Exception as e:
        logger.error(f"Overpass query failed: {e}")
        return []

    leads = []
    for el in elements[:limit]:
        tags = el.get("tags", {})
        name = tags.get("name", "").strip()
        if not name:
            continue
        phone = tags.get("phone", tags.get("contact:phone", "")).strip()
        email = tags.get("email", tags.get("contact:email", "")).strip()
        website = tags.get("website", tags.get("contact:website", "")).strip()
        address_parts = [
            tags.get("addr:housenumber", ""),
            tags.get("addr:street", ""),
            tags.get("addr:city", ""),
            tags.get("addr:postcode", ""),
        ]
        address = " ".join(p for p in address_parts if p).strip()

        leads.append({
            "name": name,
            "phone": phone,
            "email": email,
            "website": website,
            "address": address,
            "niche": niche,
            "location": location,
            "source": "overpass",
            "found_at": datetime.now().isoformat(),
            "status": "new",
        })

    return leads


def find_leads_google_places(niche, location, limit=50):
    """
    Find businesses using Google Places API.
    Requires GOOGLE_PLACES_API_KEY in .env
    """
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        logger.info("No Google Places API key - skipping")
        return []

    logger.info(f"Searching Google Places for '{niche}' in '{location}'...")
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": f"{niche} in {location}",
        "key": api_key,
    }

    leads = []
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        results = data.get("results", [])[:limit]

        for r in results:
            leads.append({
                "name": r.get("name", ""),
                "phone": "",
                "email": "",
                "website": "",
                "address": r.get("formatted_address", ""),
                "niche": niche,
                "location": location,
                "source": "google_places",
                "place_id": r.get("place_id", ""),
                "found_at": datetime.now().isoformat(),
                "status": "new",
            })

        logger.info(f"Found {len(leads)} results from Google Places")
    except Exception as e:
        logger.error(f"Google Places search failed: {e}")

    return leads


def find_leads_web_search(niche, location, limit=50):
    """
    Find businesses using web search (DuckDuckGo HTML - free, no API key).
    Extracts business names and websites from search results.
    Uses multiple queries to find individual business websites (not directories).
    """
    logger.info(f"Web searching for '{niche}' in '{location}'...")
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # Multiple queries to find actual businesses (exclude directories)
    queries = [
        f'{niche} {location} contact email -site:yellowpages.com -site:yelp.com -site:angi.com',
        f'"{niche}" "{location}" contact us',
        f'{niche} {location} website contact',
    ]

    # Directory sites to exclude from results
    directory_domains = [
        "yellowpages.com", "yelp.com", "angi.com", "homeadvisor.com",
        "facebook.com", "linkedin.com", "superpages.com", "manta.com",
        "bbb.org", "thumbtack.com", "foursquare.com", "mapquest.com",
        "wikipedia.org", "reddit.com", "indeed.com", "glassdoor.com",
        "craigslist.org", "plumbersden.com", "youtube.com",
    ]

    seen_names = set()
    leads = []

    for query in queries:
        try:
            resp = requests.post(url, data={"q": query}, headers=headers, timeout=20)
            text = resp.text

            import re
            results = re.findall(r'class="result__a"[^>]*>([^<]+)</a>', text)
            urls = re.findall(r'class="result__url"[^>]*>([^<]+)</a>', text)

            for name, web in zip(results, urls):
                if len(leads) >= limit:
                    break
                name = name.strip()
                web = web.strip()
                if not name or not web:
                    continue
                # Skip directory sites
                web_lower = web.lower()
                if any(d in web_lower for d in directory_domains):
                    continue
                # Skip duplicates
                if name.lower() in seen_names:
                    continue
                seen_names.add(name.lower())

                leads.append({
                    "name": name,
                    "phone": "",
                    "email": "",
                    "website": web,
                    "address": "",
                    "niche": niche,
                    "location": location,
                    "source": "web_search",
                    "found_at": datetime.now().isoformat(),
                    "status": "new",
                })

            if len(leads) >= limit:
                break
        except Exception as e:
            logger.error(f"Web search query '{query}' failed: {e}")

    logger.info(f"Found {len(leads)} business websites from web search")
    return leads


def find_leads(niche=None, location=None, limit=None):
    """Find leads from all available sources."""
    niche = niche or os.getenv("LEAD_SEARCH_NICHE", "plumber")
    location = location or os.getenv("LEAD_SEARCH_LOCATION", "Chicago, IL")
    limit = limit or int(os.getenv("LEAD_SEARCH_LIMIT", "50"))

    all_leads = []

    # Source 1: Overpass (free, no API key)
    all_leads.extend(find_leads_overpass(niche, location, limit))

    # Source 2: Google Places (if API key configured)
    all_leads.extend(find_leads_google_places(niche, location, limit))

    # Source 3: Web search (free fallback)
    if not all_leads:
        all_leads.extend(find_leads_web_search(niche, location, limit))

    # Deduplicate by name
    seen = set()
    unique = []
    for lead in all_leads:
        key = lead["name"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(lead)

    logger.info(f"Total unique leads found: {len(unique)}")
    save_found_leads(unique)
    return unique


def save_found_leads(leads):
    """Save found leads to a JSON file."""
    os.makedirs(os.path.dirname(LEADS_FILE), exist_ok=True)
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2)
    logger.info(f"Leads saved to {LEADS_FILE}")


def load_found_leads():
    """Load previously found leads."""
    if not os.path.exists(LEADS_FILE):
        return []
    with open(LEADS_FILE) as f:
        return json.load(f)


def get_leads_to_call():
    """Get leads that have phone numbers and haven't been called yet."""
    leads = load_found_leads()
    return [l for l in leads if l.get("phone") and l.get("status") == "new"]


def mark_lead_status(name, status):
    """Update a lead's status (new, called, interested, closed, not_interested)."""
    leads = load_found_leads()
    for lead in leads:
        if lead["name"].lower() == name.lower():
            lead["status"] = status
            break
    save_found_leads(leads)


if __name__ == "__main__":
    print("=" * 50)
    print("  LEAD FINDER")
    print("=" * 50)
    print()

    niche = os.getenv("LEAD_SEARCH_NICHE", "")
    location = os.getenv("LEAD_SEARCH_LOCATION", "")

    if niche and location:
        print(f"Searching for: {niche} in {location}")
        print()
        leads = find_leads(niche, location)
        print(f"\nFound {len(leads)} leads:")
        for i, lead in enumerate(leads[:20], 1):
            print(f"  {i}. {lead['name']} | {lead.get('phone', 'no phone')} | {lead.get('website', 'no web')}")
        if len(leads) > 20:
            print(f"  ... and {len(leads) - 20} more (saved to data/found_leads.json)")
    else:
        print("Set LEAD_SEARCH_NICHE and LEAD_SEARCH_LOCATION in your .env file.")
        print()
        print("Example:")
        print("  LEAD_SEARCH_NICHE=plumber")
        print("  LEAD_SEARCH_LOCATION=Chicago, IL")
        print()
        niche_in = input("Or enter a niche now (e.g. plumber, dentist, restaurant): ").strip()
        location_in = input("Enter a location (e.g. Chicago, IL): ").strip()
        if niche_in and location_in:
            leads = find_leads(niche_in, location_in)
            print(f"\nFound {len(leads)} leads:")
            for i, lead in enumerate(leads[:20], 1):
                print(f"  {i}. {lead['name']} | {lead.get('phone', 'no phone')}")
