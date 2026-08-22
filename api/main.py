"""FastAPI dashboard/API for ProConnect Hub.

Read-only for leads/matches. Outreach actions are draft-only and require
human approval via POST /api/outreach/{id}/approve (which still does NOT send
unless OUTREACH_ENABLED=true AND DRY_RUN=false).
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI(title="ProConnect Hub API")


def settings():
    from db.repository import get_setting
    return {
        "DRY_RUN": get_setting("DRY_RUN", "true"),
        "OUTREACH_ENABLED": get_setting("OUTREACH_ENABLED", "false"),
        "AUTO_REPLY_ENABLED": get_setting("AUTO_REPLY_ENABLED", "false"),
    }


def q(sql, params=()):
    from db.repository import fetchall
    return fetchall(sql, params)


@app.get("/health")
def health():
    try:
        q("SELECT 1")
        db = "ok"
    except Exception as e:
        db = f"error: {e}"
    return {"api": "ok", "db": db, "settings": settings()}


@app.get("/api/metrics")
def metrics():
    out = {}
    out["signals"] = q("SELECT source_platform, country_code, status, count(*) c FROM buyer_signals GROUP BY 1,2,3")
    out["opt_in"] = q("SELECT country_code, status, count(*) c FROM opt_in_leads GROUP BY 1,2")
    out["businesses"] = q("SELECT verification_status, count(*) c FROM businesses GROUP BY 1")
    out["matches"] = q("SELECT status, count(*) c FROM matches GROUP BY 1")
    out["outreach"] = q("SELECT status, count(*) c FROM outreach_queue GROUP BY 1")
    out["runs"] = q("SELECT source, status, finished_at, found FROM source_runs ORDER BY started_at DESC LIMIT 10")
    return out


@app.get("/api/needs-review")
def needs_review():
    return q("SELECT id, source_url, niche, city, country_code FROM buyer_signals WHERE status=\'needs_review\' LIMIT 100")


@app.get("/api/proposals")
def proposals():
    return q("""SELECT m.id, m.match_score, m.city_lead, m.city_business, b.name business, s.title
                FROM matches m
                JOIN businesses b ON b.id=m.business_id
                LEFT JOIN buyer_signals s ON s.id=m.lead_id
                WHERE m.status=\'proposed\' LIMIT 100""")


@app.get("/api/dry-run")
def dry_run():
    return settings()


@app.get("/", response_class=HTMLResponse)
def home():
    return """<h1>ProConnect Hub</h1>
<p>DRY-RUN mode. Endpoints: /health /api/metrics /api/proposals /api/needs-review /api/dry-run</p>"""
