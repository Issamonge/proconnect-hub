"""Add second wave of verified Reddit buyer leads."""
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEADS = os.path.join(BASE_DIR, "data", "buyer_leads.json")

NEW = [
    ("buyer", "plumber", "Looking for plumber recommendations (water heater service)",
     "https://www.reddit.com/r/lincoln/comments/1jzfp8d/looking_for_plumber_recommendations",
     "Wants someone to flush/service their water heater. Current plumber charges too much for small jobs.", "Lincoln, NE"),
    ("buyer", "plumber", "Plumber recommendations",
     "https://www.reddit.com/r/tulsa/comments/17iinmc/plumber_recommendations",
     "Looking for recommendations for a plumber/plumbing company.", "Tulsa, OK"),
    ("buyer", "plumber", "Plumber recommendations",
     "https://www.reddit.com/r/Austin/comments/1bas2a9/plumber_recommendations",
     "Has a relatively simple job, overwhelmed by choices. Wants trustworthy, reliable, not super expensive.", "Austin, TX"),
    ("buyer", "plumber", "Need reliable plumber (clogged lines)",
     "https://www.reddit.com/r/Austin/comments/rv5xoe/need_reliable_plumber",
     "Clog in house lines, further than their snake can reach. Needs bigger equipment.", "Austin, TX"),
    ("buyer", "electrician", "Looking for a decent plumber (3 leaks, sprayers, fixes)",
     "https://www.reddit.com/r/StamfordCT/comments/1h4z9p0/looking_for_a_decent_plumber",
     "Multiple accumulated jobs: 3 leaks, sprayers, shower regulator, utility sink faucet.", "Stamford, CT"),
    ("buyer", "plumber", "Looking for a plumber",
     "https://www.reddit.com/r/Knoxville/comments/1vsjhan/looking_for_a_plumber",
     "Looking for a plumber, previous posts were 1-5 years old.", "Knoxville, TN"),
    ("buyer", "plumber", "Plumber recommendations please",
     "https://www.reddit.com/r/Sacramento/comments/1vr1apl/plumber_recommendations_please",
     "Looking for plumber recommendations.", "Sacramento, CA"),
    ("buyer", "electrician", "I need an electrician and a plumber",
     "https://www.reddit.com/r/Atlanta/comments/1iekl0r/i_need_an_electrician_and_a_plumber_any",
     "Needs both an electrician and a plumber.", "Atlanta, GA"),
    ("buyer", "electrician", "Electrician recommendations (row home rewire)",
     "https://www.reddit.com/r/philadelphia/comments/1h472sr/electrician_recommendations",
     "Row home probably needs a rewire. Gathering quotes (~$25K).", "Philadelphia, PA"),
    ("buyer", "electrician", "Looking for a good electrician (outlets + recessed lighting)",
     "https://www.reddit.com/r/StLouis/comments/11wkao8/looking_for_a_good_electrician",
     "New to city, wants outlets added and recessed lighting. Creve Coeur area.", "St. Louis, MO"),
    ("buyer", "electrician", "Electrician recommendations for Mt. Airy (panel rewire + EV line)",
     "https://www.reddit.com/r/philadelphia/comments/13appxt/electrician_recommendations_for_mt_airy",
     "Buying century home. Needs panel rewire, garage EV line, induction range wiring.", "Philadelphia, PA"),
    ("buyer", "electrician", "Commercial plumber and electrician recommendations",
     "https://www.reddit.com/r/bloomington/comments/17m6mmj/commercial_plumber_and_electrician_recommendations",
     "Opening small business downtown, needs commercial plumbers and electricians for remodel.", "Bloomington, IN"),
    ("buyer", "roofing", "Need electrician and general contractor",
     "https://www.reddit.com/r/McKinney/comments/1vqrhah/need_electrician_and_general_contractor",
     "Looking for reputable electrician and general contractor with fair prices.", "McKinney, TX"),
    ("buyer", "roofing", "Looking for a roofer",
     "https://www.reddit.com/r/baltimore/comments/1vqt7ys/looking_for_a_roofer",
     "Possible dry rotted caulking. Wants honest roofers.", "Baltimore, MD"),
    ("buyer", "roofing", "Roofer recommendations for small repair",
     "https://www.reddit.com/r/Gilbert/comments/1vt1mhj/roofer_recommendations_for_small_repair",
     "Small roof repair needed, quotes $800-$2800.", "Gilbert, AZ"),
    ("buyer", "roofing", "Roofer Recommendation",
     "https://www.reddit.com/r/MorgantownWV/comments/1vrvlg6/roofer_recommendation",
     "Looking for roofer recommendations.", "Morgantown, WV"),
    ("buyer", "roofing", "Looking for reliable roofer",
     "https://www.reddit.com/r/Phillylist/comments/1vsw733/looking_for_reliable_roofer",
     "Looking for a reliable roofer.", "Philadelphia, PA"),
    ("buyer", "roofing", "Flat roof contractors",
     "https://www.reddit.com/r/ChicagoRealEstate/comments/1vp5wvr/flat_roof_contractors",
     "Looking for a roofer in Chicago area specializing in flat roofs.", "Chicago, IL"),
    ("buyer", "car_repair", "Mechanic?",
     "https://www.reddit.com/r/downriver/comments/1vuj68l/mechanic",
     "Looking for a reliable mechanic.", "Downriver, MI"),
    ("buyer", "car_repair", "Looking for a mechanic",
     "https://www.reddit.com/r/hagerstown/comments/1voy25e/looking_for_a_mechanic",
     "Looking for a mechanic.", "Hagerstown, MD"),
    ("buyer", "car_repair", "Mechanic needed",
     "https://www.reddit.com/r/baltimore/comments/1vqay0l/mechanic_needed",
     "Looking for a reliable mechanic who won't rip them off.", "Baltimore, MD"),
    ("buyer", "car_repair", "SE Seattle mechanic recommendations (Honda Fit)",
     "https://www.reddit.com/r/AskSeattle/comments/1vqhlbx/se_seattle_mechanic_recommendations",
     "Looking for a reliable mechanic for a Honda Fit in SE Seattle.", "Seattle, WA"),
    ("buyer", "car_repair", "Mechanic Recs (spark plugs)",
     "https://www.reddit.com/r/winstonsalem/comments/1vsm38j/mechanic_recs",
     "Bad experience with a shop. Needs spark plugs work.", "Winston-Salem, NC"),
]

leads = json.load(open(LEADS))
existing = {l["url"] for l in leads}
added = 0
now = datetime.now().isoformat()
for typ, niche, title, url, desc, loc in NEW:
    if url in existing:
        continue
    leads.append({
        "id": f"BUYER-2-{datetime.now().strftime('%Y%m%d%H%M%S')}-{added}",
        "type": typ, "niche": niche, "title": title, "url": url,
        "description": desc, "location": loc,
        "found_at": now, "status": "found", "matched_sellers": [],
    })
    added += 1
json.dump(leads, open(LEADS, "w"), indent=2)
print(f"Added {added} new buyer leads. Total: {len(leads)}")
