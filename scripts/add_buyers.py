"""Add verified real buyer/renter leads (found via Tavily search) to buyer_leads.json
and match them against scan_results.json businesses."""
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE_DIR, "data")

FOUND = [
    # (type, niche, title, url, description, location)
    ("buyer", "electrician", "Looking for an Electrician – Kitchen Outlets Not Working",
     "https://www.reddit.com/r/WinterGarden/comments/1vmnmka/looking_for_an_electrician_kitchen_outlets_not",
     "Need an electrician to replace kitchen outlets that stopped working.", "Winter Garden, FL"),
    ("buyer", "electrician", "How do you find a reliable electrician without paying extra",
     "https://www.reddit.com/r/electrical/comments/1vnhkqh/attention_how_do_you_find_a_reliable_electrician",
     "Tired of paying extra on online services to find local electricians. Looking for direct local providers.", ""),
    ("buyer", "roofing", "Roofers with flat or low slope experience?",
     "https://www.reddit.com/r/culvercity/comments/1vnkhml/roofers_with_flat_or_low_slope_experience",
     "Need a roofer with flat / low slope roof experience.", "Culver City, CA"),
    ("buyer", "roofing", "ISO ceiling plaster/roof repair recommendations",
     "https://www.reddit.com/r/Guelph/comments/1vs1wjx/iso_ceiling_plasterroof_repair_recommendations",
     "Looking for recommendations of someone or a company that can repair a plaster ceiling and inspect roof.", "Guelph, ON"),
    ("buyer", "roofing", "Roof repair",
     "https://www.reddit.com/r/SouthBayLA/comments/1vq2tcv/roof_repair",
     "Looking for roof repair recommendations.", "South Bay, Los Angeles, CA"),
    ("buyer", "roofing", "Roof cleaning recommendations",
     "https://www.reddit.com/r/surrey/comments/1vhxzbx/roof_cleaning_recommendations",
     "Looking for roof cleaning service recommendations.", "Surrey, BC"),
    ("buyer", "car_repair", "Trustworthy mechanic recommendations for the Gwinnett area",
     "https://www.reddit.com/r/Gwinnett/comments/1vq4sld/trustworthy_mechanic_recommendations_for_the",
     "Car needs some repair work. Looking for a trustworthy mechanic/shop that will do the job right and won't upsell.", "Gwinnett County, GA"),
    ("buyer", "car_repair", "Best shop that does oil changes well and reasonably priced",
     "https://www.reddit.com/r/rochestermn/comments/1vphp47/best_shop_that_does_oil_changes_well_and_are_also",
     "Looking for the best shop that does oil changes well and at a reasonable price.", "Rochester, MN"),
    ("buyer", "dentist", "Looking for dentist recommendations in and around Oakland",
     "https://www.reddit.com/r/oakland/comments/1l3djge/looking_for_dentist_recommendations_in_and_around",
     "Looking for a new dentist in the East Bay after a bad experience with a previous one.", "Oakland, CA"),
    ("buyer", "dentist", "Dentist Recommendations",
     "https://www.reddit.com/r/DCBitches/comments/1vpa34w/dentist_recommendations",
     "Looking for dentist recommendations. Has dental anxiety and bad past experiences.", "Washington, DC"),
    ("buyer", "dentist", "Looking for dentist recommendation",
     "https://www.reddit.com/r/mountainview/comments/1chdm4k/looking_for_dentist_recommendation",
     "Just relocated to Mountain View and needs a dentist. Delta Dental insurance, Saturdays preferred.", "Mountain View, CA"),
    ("renter", "real_estate", "Looking for apartment recommendations near Paces Ferry",
     "https://www.reddit.com/r/Smyrna/comments/1vllv5v/looking_for_apartment_recommendations_near_paces",
     "Looking for apartment recommendations near Paces Ferry area.", "Smyrna, GA"),
    ("renter", "real_estate", "Apartment Recommendations Near Madison (23F)",
     "https://www.reddit.com/r/madisonwi/comments/1vi0zoj/apartment_recommendations_near_madison_23f_under",
     "23F looking for apartment recommendations near Madison.", "Madison, WI"),
    ("renter", "real_estate", "Apartment recommendations: $1500-$1700, newer building",
     "https://www.reddit.com/r/AskChicago/comments/1vk14xe/apartment_recommendations_15001700_newer_building",
     "Looking for an apartment in Chicago, $1500-$1700 budget, newer building.", "Chicago, IL"),
    ("renter", "real_estate", "Moving to Philly this month, any apartment recommendations",
     "https://www.reddit.com/r/AskPhilly/comments/1vlrnzs/moving_to_philly_this_month_any_apartment",
     "26M moving to Philly this month. Looking for 1B1B or studio in safe locations.", "Philadelphia, PA"),
    ("renter", "real_estate", "First-Time Renter Looking for Apartment",
     "https://www.reddit.com/r/mesaaz/comments/1v3xc2p/firsttime_renter_looking_for_apartment",
     "First-time renter, $1,000-$1,200 budget, looking for apartments.", "Mesa, AZ"),
    ("renter", "real_estate", "Housing/Apartment Hunt",
     "https://www.reddit.com/r/udub/comments/1vduqde/housingapartment_hunt",
     "Student apartment hunting. Needs in-unit or on-site laundry, stove and refrigerator required.", "Seattle, WA"),
]

with open(os.path.join(DATA, "scan_results.json")) as f:
    sellers = json.load(f)
with open(os.path.join(DATA, "buyer_leads.json")) as f:
    leads = json.load(f)
existing_urls = {l.get("url") for l in leads}

added = 0
for typ, niche, title, url, desc, loc in FOUND:
    if url in existing_urls:
        continue
    matches = [s for s in sellers if s.get("niche") == niche and s.get("phone", "").strip()]
    if not matches:
        matches = [s for s in sellers if s.get("niche") == niche]
    matches = matches[:3]
    lead = {
        "id": f"{'BUYER' if typ == 'buyer' else 'RENTER'}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{added}",
        "type": typ,
        "title": title,
        "url": url,
        "description": desc,
        "location": loc,
        "found_at": datetime.utcnow().isoformat(),
        "status": "matched" if matches else "found",
        "matched_sellers": [
            {"name": m.get("name", ""), "phone": m.get("phone", ""), "location": m.get("location", "")}
            for m in matches
        ],
    }
    if typ == "buyer":
        lead["niche"] = niche
    leads.append(lead)
    added += 1

with open(os.path.join(DATA, "buyer_leads.json"), "w") as f:
    json.dump(leads, f, indent=2)
print(f"Added {added} leads. Total: {len(leads)}. Matched: {len([l for l in leads if l['status']=='matched'])}")
