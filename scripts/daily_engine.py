"""
DAILY ENGINE — runs the whole money pipeline every day, automatically.

What it does each run (designed for cron on the VPS):
  1. FIND new buyers on Reddit (Tavily API if TAVILY_API_KEY set, else DuckDuckGo)
  2. FIND businesses in each new buyer's city (DuckDuckGo, free)
  3. MATCH buyers <-> same-city businesses
  4. CREATE deals ($25 each)
  5. CONTACT businesses: verified email OR website contact form
  6. CHECK Gmail for replies and auto-respond (auto_replyer)
  7. WRITE a daily report to data/reports/YYYY-MM-DD.md

USAGE:
  python3 scripts/daily_engine.py            # full run
  python3 scripts/daily_engine.py --report   # just show today's report
"""
import os
import sys
import json
import time
import argparse
import subprocess
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE_DIR, "data")
REPORTS = os.path.join(DATA, "reports")
os.makedirs(REPORTS, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("daily_engine")

NICHES = ["plumber", "electrician", "roofing", "car_repair", "dentist", "real_estate"]
BUYER_QUERIES = {
    "plumber": 'reddit "need a plumber" OR "plumber recommendations" OR "looking for a plumber"',
    "electrician": 'reddit "need an electrician" OR "electrician recommendations"',
    "roofing": 'reddit "roofer recommendations" OR "need a roofer" OR "roof repair recommendations"',
    "car_repair": 'reddit "mechanic recommendations" OR "need a mechanic" OR "looking for a mechanic"',
    "dentist": 'reddit "dentist recommendations" OR "looking for a dentist"',
    "real_estate": 'reddit "apartment recommendations" OR "looking for an apartment" OR "moving to" apartment',
}

# Extra queries rotated per day so volume grows without repeating
ROTATION_QUERIES = [
    'reddit "landscaper recommendations" OR "need a landscaper"',
    'reddit "house cleaner recommendations" OR "cleaning service recommendations"',
    'reddit "painter recommendations" OR "need a painter" house',
    'reddit "hvac recommendations" OR "need hvac repair"',
    'reddit "moving company recommendations" OR "need movers"',
]


def load_env():
    env = {}
    p = os.path.join(BASE_DIR, ".env")
    if os.path.exists(p):
        for line in open(p):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env


def tavily_search(query, api_key, max_results=10):
    import requests
    try:
        r = requests.post("https://api.tavily.com/search", json={
            "api_key": api_key, "query": query, "max_results": max_results,
            "search_depth": "basic", "days": 7,
        }, timeout=30)
        return r.json().get("results", [])
    except Exception as e:
        log.warning(f"tavily failed: {e}")
        return []


def ddg_search_urls(query, max_results=10):
    import requests, re, html
    try:
        r = requests.get("https://html.duckduckgo.com/html/", params={"q": query},
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        links = re.findall(r'class="result__a"[^>]*href="(.*?)"', r.text)
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', r.text)
        snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        out = []
        from urllib.parse import urlparse, parse_qs
        for t, l, s in zip(titles, links, snips):
            url = html.unescape(l)
            if "uddg=" in url:
                url = parse_qs(urlparse("https:" + url if url.startswith("//") else url).query).get("uddg", [url])[0]
            clean = lambda x: html.unescape(re.sub(r"<[^>]+>", "", x)).strip()
            out.append({"title": clean(t), "url": url, "content": clean(s)})
        return out[:max_results]
    except Exception as e:
        log.warning(f"ddg failed: {e}")
        return []


def extract_location(title, snippet):
    import re
    text = f"{title} {snippet}"
    m = re.search(r'\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?,\s*(?:[A-Z]{2}|[A-Z][a-z]+))\b', text)
    if m:
        return m.group(1)
    # subreddit heuristic: r/<city>
    m = re.search(r'/r/([A-Za-z]+)', text)
    return ""


def find_buyers(env, results):
    leads_file = os.path.join(DATA, "buyer_leads.json")
    leads = json.load(open(leads_file)) if os.path.exists(leads_file) else []
    existing_urls = {l.get("url") for l in leads}
    tavily_key = env.get("TAVILY_API_KEY", "")

    # rotate one extra query per day for growing volume
    day = datetime.now(timezone.utc).timetuple().tm_yday
    queries = list(BUYER_QUERIES.items())
    extra_niche = ["landscaping", "cleaning", "painting", "hvac", "moving"][day % 5]
    queries.append((extra_niche, ROTATION_QUERIES[day % len(ROTATION_QUERIES)]))

    new_count = 0
    now = datetime.now(timezone.utc).isoformat()
    for niche, q in queries:
        hits = tavily_search(q, tavily_key) if tavily_key else ddg_search_urls(q)
        for h in hits:
            url = h.get("url", "")
            title = h.get("title", "")
            if not url or url in existing_urls or "reddit.com" not in url:
                continue
            loc = extract_location(title, h.get("content", ""))
            leads.append({
                "id": f"BUYER-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{len(leads)}",
                "type": "renter" if niche == "real_estate" else "buyer",
                "niche": niche, "title": title[:200], "url": url,
                "description": (h.get("content", "") or "")[:300],
                "location": loc, "found_at": now,
                "status": "found", "matched_sellers": [],
            })
            existing_urls.add(url)
            new_count += 1
        time.sleep(1)
    json.dump(leads, open(leads_file, "w"), indent=2)
    results["new_buyers"] = new_count
    results["total_buyers"] = len(leads)
    return new_count


def run_step(cmd, results, key, timeout=1800):
    try:
        p = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=timeout)
        tail = (p.stdout or "")[-500:]
        log.info(f"{key}: {tail.splitlines()[-1] if tail else p.returncode}")
        results[key] = "ok"
        return tail
    except Exception as e:
        log.error(f"{key} failed: {e}")
        results[key] = f"failed: {e}"
        return ""


def match_and_deal(results):
    """Match found leads with same-city sellers, create deals."""
    def city_of(loc):
        return (loc or "").lower().split(",")[0].strip()

    leads_file = os.path.join(DATA, "buyer_leads.json")
    sellers_file = os.path.join(DATA, "scan_results.json")
    deals_file = os.path.join(DATA, "deals.json")
    leads = json.load(open(leads_file))
    sellers = json.load(open(sellers_file)) if os.path.exists(sellers_file) else []
    deals = json.load(open(deals_file)) if os.path.exists(deals_file) else []
    pairs = {(d["lead_id"], d["seller_name"]) for d in deals}

    new_deals = 0
    for lead in leads:
        if lead["status"] == "matched":
            continue
        niche = lead.get("niche") or ("real_estate" if lead.get("type") == "renter" else None)
        lc = city_of(lead.get("location", ""))
        matches = [s for s in sellers if s.get("niche") == niche and (not lc or city_of(s.get("location", "")) == lc)]
        if not matches:
            continue
        matches = matches[:3]
        lead["matched_sellers"] = [{"name": s["name"], "phone": s.get("phone", ""), "location": s.get("location", "")} for s in matches]
        lead["status"] = "matched"
        for s in lead["matched_sellers"]:
            if (lead["id"], s["name"]) in pairs:
                continue
            deals.append({
                "deal_id": f"DEAL-{lead['id']}-{new_deals}",
                "lead_id": lead["id"], "lead_title": lead["title"], "lead_url": lead["url"],
                "lead_location": lead.get("location"), "lead_description": lead.get("description"),
                "seller_name": s["name"], "seller_phone": s.get("phone", ""), "seller_email": "",
                "lead_niche": niche, "lead_fee": 25, "status": "pending_contact",
                "created_at": datetime.now(timezone.utc).isoformat()})
            new_deals += 1
    json.dump(leads, open(leads_file, "w"), indent=2)
    json.dump(deals, open(deals_file, "w"), indent=2)
    results["new_deals"] = new_deals
    results["total_deals"] = len(deals)


def write_report(results):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(REPORTS, f"{today}.md")
    lines = [f"# Daily Report — {today}\n"]
    for k, v in results.items():
        lines.append(f"- **{k}**: {v}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    if args.report:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        p = os.path.join(REPORTS, f"{today}.md")
        print(open(p).read() if os.path.exists(p) else "No report today yet.")
        return

    log.info("=== DAILY ENGINE START ===")
    results = {"date": datetime.now(timezone.utc).isoformat()}
    env = load_env()

    # 1. find buyers
    find_buyers(env, results)

    # 2. find businesses in buyer cities
    run_step(["python3", "scripts/find_businesses_for_buyers.py"], results, "businesses")

    # 3+4. match + deals
    match_and_deal(results)

    # 5. contact: verified emails first
    run_step(["python3", "scripts/smart_email_sender.py"], results, "emails", timeout=3600)
    # then contact forms for what's left
    run_step(["python3", "scripts/form_filler.py"], results, "forms", timeout=3600)

    # 6. auto-reply check
    run_step(["python3", "scripts/auto_replyer.py", "--once"], results, "replies", timeout=600)

    # 7. dashboard + report
    run_step(["python3", "scripts/dashboard.py"], results, "dashboard", timeout=300)
    path = write_report(results)
    log.info(f"report: {path}")
    log.info("=== DAILY ENGINE DONE ===")


if __name__ == "__main__":
    main()
