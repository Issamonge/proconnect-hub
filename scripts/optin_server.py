"""Opt-in funnel server: /<country>/<city>/<niche> -> opt_in_lead.

Consent form records timestamp, IP, privacy acceptance. Confirms buyer and
notifies matched businesses only after valid consent.
"""
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
DATA = os.path.join(BASE, "data")

from core.models import new_lead
from core.location import normalize_location

CONFIRM_MSG = """Thank you! Your request was submitted. Local verified providers
may contact you as you consented below. Reference: {id}. This link is confirmation
and creates an opt_in_lead in our system."""


def submit_lead(country_code, city, niche, service, timeframe, contact, name, email, phone, consent, ip, ua):
    try:
        rec = new_lead(
            lead_type="opt_in_lead",
            source_platform="landing_page",
            country=normalize_location(city, hint_country=country_code),
            niche=niche,
            requested_service=service,
            summary=f"{service} needed in {city}",
            consent_status="opt_in_consent",
            contact_permission=True,
            contact_details={"name": name, "email": email, "phone": phone, "prefer": contact},
            status="new",
        )
    except ValueError:
        return None
    rec["consent"] = {
        "timestamp": time.time(),
        "ip": ip,
        "user_agent": ua,
        "text": "Selected local providers may contact me about my request.",
    }
    leads = json.load(open(os.path.join(DATA, "leads.json"))) if os.path.exists(os.path.join(DATA, "leads.json")) else []
    leads.append(rec)
    json.dump(leads, open(os.path.join(DATA, "leads.json"), "w"), indent=2)
    return rec["id"]


def render_form(country_code, city, niche, service=""):
    countries = json.load(open(os.path.join(BASE, "config", "countries.json")))
    niches = json.load(open(os.path.join(BASE, "config", "niches.json")))
    label = niches.get(niche, {}).get("label", niche.replace("_", " "))
    country = countries.get(country_code, {}).get("name", country_code)

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Get matched — {label} in {city}</title>
<style>
body{{font-family:sans-serif;max-width:520px;margin:40px auto;padding:0 20px}}
input,select{{width:100%;padding:10px;margin:4px 0;border:1px solid #ccc;border-radius:4px}}
button{{width:100%;padding:12px;background:#0066cc;color:#fff;border:none;border-radius:4px;cursor:pointer}}
label{{font-size:14px}}
h1{{font-size:22px}}
</style></head><body>
<h1>Find a {label} in {city}</h1>
<p>Free matching with verified local providers. Submit your request below.</p>
<form method="POST" action="">
<input type="hidden" name="service" value="{service or label}">
<label>Your name <input name="name" required></label>
<label>What do you need? <input name="service_detail" value="{service}" placeholder="e.g. water heater flush"></label>
<label>When? <select name="timeframe"><option>asap</option><option>this week</option><option>this month</option></select></label>
<label>Contact: <select name="contact"><option>email</option><option>phone</option></select></label>
<label>Email <input name="email" type="email"></label>
<label>Phone <input name="phone"></label>
<label style="margin:10px 0;display:block">
  <input type="checkbox" name="consent" required style="width:auto">
  I consent that selected local providers may contact me about this request. •
  <a href="/privacy">Privacy policy</a>
</label>
<button>Get matched</button>
</form>
</body></html>"""


def handle(handler):
    parsed = urlparse(handler.path)
    parts = [p for p in parsed.path.split("/") if p]

    if "/privacy" == parsed.path:
        body = """<h1>Privacy</h1><p>We store your name, contact preference, and request solely to match you with
verified local providers in your area. You may withdraw consent anytime: ihakizimana11@gmail.com</p>"""
        return body.encode()

    if len(parts) != 3:
        return ("<h2>Opt-in funnel</h2><p>URL format: /&lt;country&gt;/&lt;city&gt;/&lt;niche&gt;</p>").encode()

    if handler.command == "GET":
        country, city, niche = parts[0].upper(), parts[1], parts[2]
        return render_form(country, city.replace("_", " ").title(), niche).encode()

    if handler.command == "POST":
        country, city, niche = parts[0].upper(), parts[1], parts[2]
        ln = int(handler.headers.get("Content-Length", 0))
        body = handler.rfile.read(ln).decode()
        form = parse_qs(body)
        getv = lambda k: form.get(k, [""])[0]
        if getv("consent") != "on":
            return b"Consent required."
        name = getv("name")
        email = getv("email")
        phone = getv("phone")
        service = getv("service_detail")
        contact = getv("contact")
        timeframe = getv("timeframe")
        ip = getattr(handler, "client_address", ["-"]) [0]
        ua = handler.headers.get("User-Agent", "")
        lead_id = submit_lead(country, city.replace("_", " ").title(), niche, service, timeframe, contact, name, email, phone, True, ip, ua)
        if not lead_id:
            return b"Invalid request."
        for b in json.load(open(os.path.join(DATA, "businesses.json"))) if os.path.exists(os.path.join(DATA, "businesses.json")) else []:
            if b.get("niche") == niche and b.get("country", {}).get("city", "").lower() == (parts[1].replace("_", " ").title()).lower():
                sys.stdout.write(f"NOTIFY {b['name']}\n")
        return CONFIRM_MSG.format(id=lead_id).encode()
    return b"ok"


class Handler(BaseHTTPRequestHandler):
    def _resp(self):
        body = handle(self)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self): self._resp()
    def do_POST(self): self._resp()


def serve(port=12001):
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 12001
    serve(port)
