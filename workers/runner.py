"""Modular workers for ProConnect Hub. All workers respect DRY_RUN/OUTREACH_ENABLED
from app_settings — they never send emails or auto-reply when those flags are on.

Entry point: python3 -m workers.runner <task>
tasks: discover_buyers | discover_businesses | match | backup | cleanup
"""
import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def log(msg):
    line = f"[worker] {time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)


def flags():
    from db.repository import get_setting
    return {
        "DRY_RUN": get_setting("DRY_RUN", "true") == "true",
        "OUTREACH": get_setting("OUTREACH_ENABLED", "false") == "true",
        "AUTO_REPLY": get_setting("AUTO_REPLY_ENABLED", "false") == "true",
    }


def discover_buyers():
    f = flags()
    if not f["DRY_RUN"]:
        log("DRY_RUN=false — discovery still allowed (no sends), but be careful.")
    from sources import fetch
    from db.repository import insert_signal, fetchall
    from core.location import normalize_location
    import json as _json
    niches_cfg = _json.load(open("config/niches.json"))
    countries_cfg = _json.load(open("config/countries.json"))
    n = 0
    for cc, cfg in countries_cfg.items():
        for niche in niches_cfg:
            try:
                for rec in fetch(niche, [cc]):
                    loc = normalize_location(rec.get("location_hint", ""), hint_country=cc)
                    insert_signal({
                        "source_platform": rec.get("source_platform", "unknown"),
                        "source_url": rec.get("url", ""),
                        "niche": niche,
                        "title": rec.get("title", "")[:200],
                        "summary": (rec.get("snippet") or "")[:400],
                        "country_code": loc.get("country_code"),
                        "city": loc.get("city"),
                        "status": "new" if loc.get("confidence") == "city" else "needs_review",
                    })
                    n += 1
            except Exception as e:
                log(f"discover {niche}/{cc} error: {e}")
    log(f"discover_buyers done: +{n}")


def discover_businesses():
    log("discover_businesses: uses existing rebuild_businesses.py output")
    subprocess_run = __import__("subprocess").run
    r = subprocess_run(["python3", "scripts/rebuild_businesses.py"], capture_output=True, text=True)
    log((r.stdout or "")[-200:])


def match():
    from db.repository import fetchall, execute
    signals = fetchall("SELECT * FROM buyer_signals WHERE status=\'new\'")
    biz = fetchall("SELECT * FROM businesses WHERE verification_status=\'verified\' AND do_not_contact=false")
    made = 0
    for lead in signals:
        if not lead.get("city"):
            execute("UPDATE buyer_signals SET status=\'needs_review\' WHERE id=%s", (lead["id"],))
            continue
        matches = [b for b in biz if b["niche"] == lead["niche"]
                   and b.get("city") and b["city"].lower() == lead["city"].lower()][:3]
        for m in matches:
            execute("""INSERT INTO matches (lead_kind, lead_id, business_id, match_score, city_lead, city_business)
                       VALUES (\'intent_signal\', %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                    (lead["id"], m["id"], 60, lead["city"], m["city"]))
            made += 1
        if matches:
            execute("UPDATE buyer_signals SET status=\'matched\' WHERE id=%s", (lead["id"],))
    log(f"match: +{made}")


def backup():
    import subprocess
    ts = time.strftime("%Y%m%d-%H%M")
    os.makedirs("backups", exist_ok=True)
    out = f"backups/proconnect-{ts}.sql.gz"
    cmd = f"pg_dump $DATABASE_URL | gzip > {out}"
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    log(f"backup -> {out} rc={r.returncode}")


def cleanup():
    from db.repository import execute
    execute("""UPDATE buyer_signals SET status=\'archived\'
               WHERE status=\'new\' AND created_at < now() - interval \'7 days\'""")
    log("cleanup: archived stale signals")


TASKS = {"discover_buyers": discover_buyers, "discover_businesses": discover_businesses,
         "match": match, "backup": backup, "cleanup": cleanup}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in TASKS:
        print("usage: python3 -m workers.runner " + "|".join(TASKS))
        sys.exit(1)
    TASKS[sys.argv[1]]()


if __name__ == "__main__":
    main()
