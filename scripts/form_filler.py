"""CONTACT FORM AUTO-FILLER — submits our offer via business websites' contact forms.

For each matched seller:
1. Open their website (headless Chromium)
2. Look for a contact form (name/email/message fields)
3. Fill it with our offer and submit
4. Mark the deal "form_submitted"

No email bounces — the message lands directly in the business's inbox/CMS.

USAGE:
  python3 scripts/form_filler.py --dry   # show which sites/forms found
  python3 scripts/form_filler.py         # submit forms
"""
import os
import sys
import json
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE_DIR, "data")

OFFER = (
    "Hello! I run ProConnect Hub — we connect businesses with customers. "
    "I have a customer in {loc} who needs a {niche} right now. "
    "Would you like this customer lead? The lead fee is $25 only if you want the customer's contact info. "
    "Reply to this message or email ihakizimana11@gmail.com and I will send the details. Thanks!"
)

FROM_NAME = "ProConnect Hub"
FROM_EMAIL = "ihakizimana11@gmail.com"


def load_targets():
    deals = json.load(open(os.path.join(DATA, "deals.json")))
    sellers = json.load(open(os.path.join(DATA, "scan_results.json")))
    by_name = {s["name"].lower(): s for s in sellers}
    out = []
    seen = set()
    for d in deals:
        if d.get("status") in ("form_submitted",):
            continue
        s = by_name.get(d["seller_name"].lower())
        if not s or not s.get("website"):
            continue
        key = s["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append((d, s))
    return out


def find_contact_page(page, base):
    links = page.eval_on_selector_all("a", "els => els.map(e => e.href)")
    for l in links:
        if not l or not l.startswith("http"):
            continue
        if any(k in l.lower() for k in ["/contact", "/contact-us", "/get-in-touch", "/reach"]):
            if l.split("/")[2] in base:
                return l
    return None


def has_form(page):
    """Detect a contact form WITHOUT filling (used in dry mode)."""
    try:
        email = page.query_selector('input[type="email"], input[name*="email" i], input[name*="e-mail" i], input[id*="email" i]')
        msg = page.query_selector('textarea')
        return bool(email and msg)
    except Exception:
        return False


def try_form(page, dry=False):
    """Try to find and fill a contact form. Returns True if found (dry) or submitted."""
    name_sels = ['input[name*="name" i]', 'input[id*="name" i]']
    email_sels = ['input[type="email"]', 'input[name*="email" i]', 'input[name*="e-mail" i]', 'input[id*="email" i]']
    msg_sels = ['textarea[name*="message" i]', 'textarea[name*="comment" i]',
                'textarea[id*="message" i]', 'textarea']

    if not has_form(page):
        return False
    if dry:
        return True

    def fill(sels, value):
        for sel in sels:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.fill(value)
                    return True
            except Exception:
                continue
        return False

    got_name = fill(name_sels, FROM_NAME)
    got_email = fill(email_sels, FROM_EMAIL)
    got_msg = fill(msg_sels, OFFER_TXT)
    if not (got_email and got_msg):
        return False
    if not got_name:
        fill(['input[name*="first" i]'], "ProConnect")
    fill(['input[name*="phone" i]', 'input[type="tel"]'], "")

    # submit
    for sel in ['button[type="submit"]', 'input[type="submit"]', 'button:has-text("Send")',
                'button:has-text("Submit")', 'button:has-text("Contact")']:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(2500)
                return True
        except Exception:
            continue
    # try form.submit
    try:
        page.eval_on_selector("form", "f => f.submit()")
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()

    global OFFER_TXT
    targets = load_targets()
    print(f"Sellers with websites to try: {len(targets)}")

    from playwright.sync_api import sync_playwright
    submitted, failed = 0, 0
    deals_file = os.path.join(DATA, "deals.json")
    deals = json.load(open(deals_file))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        for deal, seller in targets:
            OFFER_TXT = OFFER.format(loc=deal.get("lead_location") or "your area",
                                     niche=deal.get("lead_niche", "service"))
            url = seller["website"]
            page = ctx.new_page()
            ok = False
            try:
                page.goto(url, timeout=15000)
                page.wait_for_timeout(1500)
                ok = try_form(page, dry=args.dry)
                if not ok:
                    contact = find_contact_page(page, url)
                    if contact:
                        page.goto(contact, timeout=15000)
                        page.wait_for_timeout(1500)
                        ok = try_form(page, dry=args.dry)
            except Exception as e:
                print("err", url[:50], str(e)[:60])
            page.close()

            mark = "found form" if ok else "no form"
            print(("✅" if ok else "❌"), seller["name"][:40], "->", mark)
            if ok and not args.dry:
                for i, d in enumerate(deals):
                    if d["deal_id"] == deal["deal_id"]:
                        deals[i]["status"] = "form_submitted"
                submitted += 1
            else:
                failed += 1
        browser.close()

    if not args.dry:
        json.dump(deals, open(deals_file, "w"), indent=2)
    print(f"\nSubmitted to {submitted} | no form: {failed}")


if __name__ == "__main__":
    OFFER_TXT = ""
    main()
