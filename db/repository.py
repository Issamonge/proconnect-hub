"""PostgreSQL repository layer. DB-first; JSON files are legacy/import-only.
Connection string comes from DATABASE_URL env (never hardcoded).
All methods are pure data access - no sending, no side effects.
"""
import os
import json


def get_conn():
    import psycopg2
    url = os.environ["DATABASE_URL"]
    return psycopg2.connect(url)


def fetchall(sql, params=()):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def execute(sql, params=()):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()


def insert(table, row):
    cols = ", ".join(row.keys())
    phs = ", ".join(["%s"] * len(row))
    execute(f"INSERT INTO {table} ({cols}) VALUES ({phs}) ON CONFLICT DO NOTHING",
            tuple(row.values()))


def get_setting(key, default=None):
    rows = fetchall("SELECT value FROM app_settings WHERE key=%s", (key,))
    return rows[0]["value"] if rows else default


def set_setting(key, value):
    execute(
        "INSERT INTO app_settings (key, value, updated_at) VALUES (%s,%s,now()) "
        "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()",
        (key, value))


def insert_signal(rec):
    """Insert an intent_signal. Contact fields are never accepted here."""
    allowed = {"source_platform","source_url","source_post_date","country_code","region",
               "city","normalized_location","latitude","longitude","niche",
               "requested_service","urgency","language","title","summary",
               "freshness_score","quality_score","status","evidence"}
    row = {k: v for k, v in rec.items() if k in allowed}
    insert("buyer_signals", row)


def insert_opt_in(rec):
    row = {k: v for k, v in rec.items() if k in {
        "country_code","region","city","normalized_location","latitude","longitude",
        "niche","requested_service","urgency","language","summary",
        "contact_name","contact_email","contact_phone","contact_preference",
        "consent_text","consent_at","consent_ip","consent_user_agent",
        "privacy_accepted","status"}}
    if not row.get("privacy_accepted"):
        raise ValueError("opt-in requires privacy_accepted=true")
    insert("opt_in_leads", row)


def insert_business(rec):
    allowed = {"name","niche","country_code","region","city","normalized_location",
               "service_radius_km","address","phone","official_website","source_urls",
               "verification_status","contact_preference","language","do_not_contact","notes"}
    row = {k: v for k, v in rec.items() if k in allowed}
    insert("businesses", row)


def import_json_legacy():
    """One-time import of legacy JSON (buyer_leads.json -> buyer_signals)."""
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    src = os.path.join(base, "buyer_leads.json")
    if not os.path.exists(src):
        return 0
    n = 0
    for l in json.load(open(src)):
        insert_signal({
            "source_platform": "reddit" if "reddit" in l.get("url","") else "legacy",
            "source_url": l.get("url",""),
            "niche": l.get("niche") or "real_estate",
            "title": l.get("title","")[:200],
            "summary": l.get("description","")[:400],
            "status": "needs_review",
        })
        n += 1
    return n
