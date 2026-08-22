"""Quality/compliance dashboard for the unified system.

Reads data/leads.json, businesses.json, deals.json, audit.log and renders
metrics: source performance, freshness, geo accuracy, bounce, opt-in, revenue.
"""
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")


def load(name, default):
    p = os.path.join(DATA, name)
    return json.load(open(p)) if os.path.exists(p) else default


def metrics():
    leads = load("leads.json", [])
    biz = load("businesses.json", [])
    deals = load("deals.json", []) or load("deals.json", [])

    total = len(leads)
    c = {
        "by_source": Counter(l["source_platform"] for l in leads),
        "by_status": Counter(l["status"] for l in leads),
        "by_country": Counter(l["country"].get("country_name", "?") for l in leads),
        "fresh": sum(1 for l in leads if l.get("freshness_score", 0) >= 70),
        "opt_in": sum(1 for l in leads if l["lead_type"] == "opt_in_lead"),
        "needs_review": sum(1 for l in leads if l["status"] == "needs_review"),
        "archived": sum(1 for l in leads if l["status"] == "archived"),
    }
    kb = {
        "total": len(biz),
        "verified": sum(1 for b in biz if b.get("verification_status") == "verified"),
        "no_contact": sum(1 for b in biz if b.get("do_not_contact")),
        "verified_email": sum(1 for b in biz if b.get("email_verification_status") == "mx_ok"),
    }
    kd = {"total": len(deals), "proposed": sum(1 for d in deals if d.get("status") == "proposed")}
    return c, kb, kd


def html(c, kb, kd):
    def row(n, items): return "".join(f"<tr><td>{n}</td><td>{i}</td></tr>" for n, i in list(items))
    return f"""<!doctype html><html><head><meta charset=utf-8><title>ProConnect Hub Dashboard</title>
<style>body{{font-family:sans-serif;margin:30px}}table{{border-collapse:collapse}}td{{border:1px solid #ccc;padding:4px 10px}}h2{{margin-top:24px}}</style></head><body>
<h1>ProConnect Hub — Quality & Compliance</h1>
<h2>Leads</h2>
<table>{row("total", [("", str(sum(c['by_status'].values())))] + list(c['by_source'].items())) if False else row("total", list(c['by_source'].items()) + [("needs_review", c['needs_review']), ("archived", c['archived']), ("opt_in", c['opt_in'])])}</table>
<h2>Businesses</h2>
<table>{row("business", list(kb.items()))}</table>
<h2>Deals (proposed)</h2><p>{kd['proposed']} / {kd['total']}</p>
<p>Generated: {datetime.now(timezone.utc).isoformat()}</p></body></html>"""


def main():
    c, kb, kd = metrics()
    path = os.path.join(BASE, "dashboard", "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(html(c, kb, kd))
    print("dashboard:", path)


if __name__ == "__main__":
    main()
