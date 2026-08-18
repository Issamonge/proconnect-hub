#!/usr/bin/env python3
"""
Compile leads found via Tavily search into scan_results.json format,
then extract emails and send outreach.
"""
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
RESULTS_FILE = os.path.join(DATA_DIR, "scan_results.json")

# Leads found via Tavily search - real businesses with real emails
NEW_LEADS = [
    # Dentists - Phoenix, AZ
    {"name": "Harris Dental", "website": "https://www.harrisdental.com", "email": "", "phone": "480-428-0040", "niche": "dentist", "scan_niche": "dentist", "scan_city": "Phoenix, AZ"},
    {"name": "Pearl Dental", "website": "http://pearldentalaz.com", "email": "contact@pearldentalaz.info", "phone": "602-899-6950", "niche": "dentist", "scan_niche": "dentist", "scan_city": "Phoenix, AZ"},
    {"name": "Arizona Dental", "website": "https://arizonadental.com", "email": "", "phone": "602-788-4040", "niche": "dentist", "scan_niche": "dentist", "scan_city": "Phoenix, AZ"},
    {"name": "Dental on Central", "website": "https://dentaloncentral.com", "email": "", "phone": "602-266-1776", "niche": "dentist", "scan_niche": "dentist", "scan_city": "Phoenix, AZ"},
    {"name": "Kevin Ortale DDS", "website": "https://www.kevinortaledds.com", "email": "", "phone": "", "niche": "dentist", "scan_niche": "dentist", "scan_city": "Phoenix, AZ"},

    # Electricians - Houston, TX
    {"name": "Raw Electrical Services", "website": "http://www.rawelectricalservices.net", "email": "", "phone": "281-606-0829", "niche": "electrician", "scan_niche": "electrician", "scan_city": "Houston, TX"},

    # Car Repair - San Diego, CA
    {"name": "MR Auto SD", "website": "https://mrautosd.com", "email": "", "phone": "858-455-8222", "niche": "car_repair", "scan_niche": "car_repair", "scan_city": "San Diego, CA"},
    {"name": "Morena Automotive", "website": "https://www.morenaauto.com", "email": "", "phone": "619-276-3263", "niche": "car_repair", "scan_niche": "car_repair", "scan_city": "San Diego, CA"},
    {"name": "Coastal Auto Repair", "website": "https://carpb.com", "email": "coastalautorepairpb@gmail.com", "phone": "858-412-4990", "niche": "car_repair", "scan_niche": "car_repair", "scan_city": "San Diego, CA"},
    {"name": "Pacific Auto Service", "website": "https://pacificautoservice.com", "email": "", "phone": "858-271-8006", "niche": "car_repair", "scan_niche": "car_repair", "scan_city": "San Diego, CA"},
    {"name": "John's Automotive Care", "website": "https://www.johnssandiegoautorepair.com", "email": "", "phone": "619-280-9315", "niche": "car_repair", "scan_niche": "car_repair", "scan_city": "San Diego, CA"},

    # Lawyers - Philadelphia, PA
    {"name": "Law Offices of Michael S. Bomstein", "website": "https://www.pinnolabomstein.com", "email": "", "phone": "215-592-8383", "niche": "lawyer", "scan_niche": "lawyer", "scan_city": "Philadelphia, PA"},
    {"name": "Weisberg Law", "website": "https://www.weisberglawoffices.com", "email": "", "phone": "610-550-8042", "niche": "lawyer", "scan_niche": "lawyer", "scan_city": "Philadelphia, PA"},
    {"name": "Sidkoff Pincus & Green", "website": "https://www.greatlawyers.com", "email": "", "phone": "215-574-0600", "niche": "lawyer", "scan_niche": "lawyer", "scan_city": "Philadelphia, PA"},
    {"name": "Chamberlain Hrdlicka", "website": "https://www.chamberlainlaw.com", "email": "firm@chamberlainlaw.com", "phone": "610-772-2300", "niche": "lawyer", "scan_niche": "lawyer", "scan_city": "Philadelphia, PA"},

    # Veterinary - Austin, TX
    {"name": "Crestview Veterinary Clinic", "website": "https://crestviewvc.com", "email": "", "phone": "512-535-2100", "niche": "veterinary", "scan_niche": "veterinary", "scan_city": "Austin, TX"},
    {"name": "Paz Veterinary North", "website": "https://paznorth.com", "email": "ReceptionNorth@PAZvet.com", "phone": "512-236-8000", "niche": "veterinary", "scan_niche": "veterinary", "scan_city": "Austin, TX"},
    {"name": "Bee Cave Veterinary Clinic", "website": "https://beecavevet.com", "email": "", "phone": "", "niche": "veterinary", "scan_niche": "veterinary", "scan_city": "Austin, TX"},
    {"name": "Honnas Veterinary", "website": "https://honnasvet.com", "email": "", "phone": "", "niche": "veterinary", "scan_niche": "veterinary", "scan_city": "Austin, TX"},

    # Real Estate - Columbus, OH
    {"name": "Chris Lancaster Real Estate", "website": "https://www.coldwellbankerhomes.com/oh/columbus/agent/chris-lancaster/aid_7744", "email": "chris.lancaster@kingthompson.com", "phone": "614-570-1366", "niche": "real_estate", "scan_niche": "real_estate", "scan_city": "Columbus, OH"},
    {"name": "Affordable Real Estate Columbus", "website": "https://www.afford-realestate.com", "email": "", "phone": "614-884-3300", "niche": "real_estate", "scan_niche": "real_estate", "scan_city": "Columbus, OH"},
    {"name": "e-Merge Real Estate", "website": "https://www.e-merge.com", "email": "info@e-merge.com", "phone": "800-644-6637", "niche": "real_estate", "scan_niche": "real_estate", "scan_city": "Columbus, OH"},
    {"name": "Ferrari Home Group", "website": "https://www.ferrarihomegroup.com", "email": "", "phone": "", "niche": "real_estate", "scan_niche": "real_estate", "scan_city": "Columbus, OH"},

    # Roofing - Jacksonville, FL
    {"name": "Jacksonville Roofing Company", "website": "https://www.jax-roofing.com", "email": "", "phone": "904-257-8093", "niche": "roofing", "scan_niche": "roofing", "scan_city": "Jacksonville, FL"},
    {"name": "Top Gun Roofing", "website": "https://topgunroofingjax.com", "email": "", "phone": "904-342-0211", "niche": "roofing", "scan_niche": "roofing", "scan_city": "Jacksonville, FL"},
    {"name": "The Roofing Company Inc", "website": "https://theroofingcompanyfl.com", "email": "info.theroofingcompany@gmail.com", "phone": "904-800-3751", "niche": "roofing", "scan_niche": "roofing", "scan_city": "Jacksonville, FL"},
    {"name": "Jack C. Wilson Roofing", "website": "https://www.jackcwilsonroofing.com", "email": "jcwroof@jcwroof.com", "phone": "904-396-1546", "niche": "roofing", "scan_niche": "roofing", "scan_city": "Jacksonville, FL"},
    {"name": "E2 Roofing Jacksonville", "website": "https://e2roofingjax.com", "email": "", "phone": "904-420-8844", "niche": "roofing", "scan_niche": "roofing", "scan_city": "Jacksonville, FL"},
    {"name": "Heritage Construction Group", "website": "https://www.heritagenfl.com", "email": "Erica@HeritageNFL.com", "phone": "", "niche": "roofing", "scan_niche": "roofing", "scan_city": "Jacksonville, FL"},
    {"name": "SPC Roofers", "website": "https://www.spcroofers.com", "email": "", "phone": "904-647-5945", "niche": "roofing", "scan_niche": "roofing", "scan_city": "Jacksonville, FL"},
]

def main():
    # Load existing leads
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            existing = json.load(f)
    else:
        existing = []

    # Get existing websites to avoid duplicates
    existing_websites = set()
    for l in existing:
        w = l.get("website", "").lower().rstrip("/")
        if w:
            existing_websites.add(w)

    # Add new leads
    added = 0
    for lead in NEW_LEADS:
        w = lead.get("website", "").lower().rstrip("/")
        if w in existing_websites:
            continue
        lead["location"] = lead.get("scan_city", "")
        lead["source"] = "tavily_search"
        lead["found_at"] = datetime.now().isoformat()
        lead["status"] = "new"
        existing.append(lead)
        existing_websites.add(w)
        added += 1

    # Save
    with open(RESULTS_FILE, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"Added {added} new leads. Total now: {len(existing)}")

    # Also update extracted_emails.json with leads that already have emails
    extracted_file = os.path.join(DATA_DIR, "extracted_emails.json")
    if os.path.exists(extracted_file):
        with open(extracted_file) as f:
            extracted = json.load(f)
    else:
        extracted = []

    existing_emails = set(e.get("email", "").lower() for e in extracted)

    for lead in existing:
        email = lead.get("email", "")
        if email and email.lower() not in existing_emails:
            extracted.append({
                "name": lead.get("name", ""),
                "email": email,
                "website": lead.get("website", ""),
                "niche": lead.get("scan_niche", lead.get("niche", "")),
                "city": lead.get("scan_city", ""),
                "phone": lead.get("phone", ""),
            })
            existing_emails.add(email.lower())

    with open(extracted_file, "w") as f:
        json.dump(extracted, f, indent=2)

    print(f"Total emails ready to send: {len(extracted)}")

if __name__ == "__main__":
    main()
