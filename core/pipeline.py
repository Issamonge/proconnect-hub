"""Unified pipeline CLI.

USAGE:
  python3 -m core.pipeline discover --niches plumbing roofing --countries US GB AE
  python3 -m core.pipeline verify-businesses
  python3 -m core.pipeline match
  python3 -m core.pipeline outreach            # dry-run preview only
"""
import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
sys.path.insert(0, BASE)

from core.location import normalize_location
from core.models import new_lead

def log(msg):
    line = f"{datetime.now(timezone.utc).isoformat()} {msg}"
    print(line)
    with open(os.path.join(DATA, "audit.log"), "a") as f:
        f.write(line + "\n")


def load(name, default):
    p = os.path.join(DATA, name)
    return json.load(open(p)) if os.path.exists(p) else default


def save(name, obj):
    json.dump(obj, open(os.path.join(DATA, name), "w"), indent=2)


def _now():
    return datetime.now(timezone.utc).isoformat()


def freshness_score(created_utc=None):
    if created_utc is None:
        return 75  # unknown timestamp stays eligible
    try:
        age = (time.time() - float(created_utc)) / 86400
    except Exception:
        return 75
    if age <= 1: return 100
    if age <= 3: return 90
    if age <= 7: return 75
    return 20


def discover(niches, countries):
    from sources import fetch
    leads = load("leads.json", [])
    existing_urls = {l.get("source_url") for l in leads}
    new = 0
    for niche in niches:
        for rec in fetch(niche, countries):
            url = rec.get("url", "")
            if not url or url in existing_urls:
                continue
            loc = normalize_location(rec.get("location_hint", ""))
            lead = new_lead(
                lead_type="intent_signal",
                source_platform=rec.get("source_platform", "unknown"),
                source_url=url,
                niche=niche,
                title=rec.get("title", "")[:200],
                summary=(rec.get("snippet") or "")[:400],
                country=loc,
                source_post_date=rec.get("created_utc"),
            )
            lead["freshness_score"] = freshness_score(rec.get("created_utc"))
            lead["quality_score"] = 60 if loc.get("confidence") == "city" else 30
            lead["status"] = "new" if loc.get("confidence") == "city" else "needs_review"
            leads.append(lead)
            existing_urls.add(url)
            new += 1
        time.sleep(1)
    save("leads.json", leads)
    log(f"discover: +{new} leads (total {len(leads)})")
    return new


def verify_businesses():
    import dns.resolver
    JUNK = ("johndoe", "example@", "u@domain", "email@", "noreply", "no-reply",
            "mailer-daemon", "sentry", "wixpress", "test@", ".png", ".jpg", ".jpeg")
    biz = load("businesses.json", [])
    verified = 0
    for b in biz:
        if b.get("verification_status") == "verified":
            continue
        ok = bool(b.get("official_website", "").startswith("http"))
        if b.get("public_business_email"):
            e = b["public_business_email"].lower()
            if any(j in e for j in JUNK):
                b["email_verification_status"] = "junk"
                ok = False
            else:
                try:
                    dns.resolver.resolve(e.split("@")[1], "MX", lifetime=5)
                    b["email_verification_status"] = "mx_ok"
                except Exception:
                    b["email_verification_status"] = "mx_fail"
                    ok = False
        if ok:
            b["verification_status"] = "verified"
            verified += 1
    save("businesses.json", biz)
    log(f"verify-businesses: {verified}/{len(biz)} verified")
    return verified


def match():
    leads = load("leads.json", [])
    biz = load("businesses.json", [])
    deals = load("deals.json", [])
    pairs = {(d["lead_id"], d["business_id"]) for d in deals}
    new_deals = 0
    for lead in leads:
        if lead["status"] != "new":
            continue
        if lead["freshness_score"] < 70:
            lead["status"] = "archived"
            continue
        if lead["country"].get("confidence") != "city":
            lead["status"] = "needs_review"
            continue
        city = lead["country"].get("city")
        matches = []
        for b in biz:
            if not b.get("do_not_contact") and b.get("niche") == lead["niche"] \
               and b.get("verification_status") == "verified":
                bc = b.get("country", {}).get("city")
                if bc and city and bc.lower() == city.lower():
                    matches.append(b)
        matches = matches[:3]
        if not matches:
            continue
        for m in matches:
            if (lead["id"], m["id"]) in pairs:
                continue
            score = 20
            if m.get("phone"): score += 30
            if m.get("official_website"): score += 20
            if m.get("public_business_email"): score += 20
            score += lead.get("freshness_score", 0) // 3
            deals.append({
                "deal_id": "DEAL-" + uuid.uuid4().hex[:8],
                "lead_id": lead["id"],
                "business_id": m["id"],
                "business_name": m["name"],
                "lead_title": lead["title"],
                "lead_url": lead["source_url"],
                "lead_city": city,
                "lead_niche": lead["niche"],
                "status": "proposed",
                "match_score": min(100, score),
                "created_at": _now(),
            })
            new_deals += 1
        lead["status"] = "matched"
        lead["matched_business_ids"] = [m["id"] for m in matches]
    save("leads.json", leads)
    save("deals.json", deals)
    log(f"match: +{new_deals} deals (total {len(deals)})")
    return new_deals


def outreach():
    deals = load("deals.json", [])
    biz = load("businesses.json", [])
    by_id = {b["id"]: b for b in biz}
    to_show = [d for d in deals if d["status"] == "proposed"]
    print("=" * 70)
    print("OUTREACH PREVIEW  • DRY-RUN (nothing sent)")
    print("=" * 70)
    for d in to_show[:50]:
        b = by_id.get(d["business_id"], {})
        print(f"""
--- {d['deal_id']} ---
Lead: {d['lead_title'][:60]}
Source: {d['lead_url'][:70]}
City/Niche: {d['lead_city']} / {d['lead_niche']}
Business: {d['business_name']} ({b.get('official_website','')[:40]})
Email: {b.get('public_business_email') or 'none public'}
Match score: {d['match_score']}
Preview subject: New customer inquiry in your area
Preview body: We detected a recent public request for {d['lead_niche']} in
  {d['lead_city']}. We can help you respond through a compliant referral
  workflow. No private customer details are available until the requester opts in.""")
    if to_show:
        print("\n>>> To send any of these, say: APPROVE SEND <<<")
    return len(to_show)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("discover")
    p1.add_argument("--niches", nargs="+", required=True)
    p1.add_argument("--countries", nargs="+", required=True)
    sub.add_parser("verify-businesses")
    sub.add_parser("match")
    sub.add_parser("outreach")
    args = ap.parse_args()
    if args.cmd == "discover":
        discover(args.niches, args.countries)
    elif args.cmd == "verify-businesses":
        verify_businesses()
    elif args.cmd == "match":
        match()
    elif args.cmd == "outreach":
        outreach()


if __name__ == "__main__":
    main()
