# Project Memory — ProConnect Hub (GLOBAL UPGRADE)

## ⚠️ READ THIS FIRST
The system was completely rebuilt on 2026-08-22 into a unified multi-source
structure: `core/`, `sources/`, `config/`. Old JSON files were migrated.

## Unified architecture
- `core/location.py` — city/region/country normalization + haversine distance
- `core/models.py` — lead/business records; migration → leads.json, businesses.json
- `core/pipeline.py` — discover → verify-businesses → match → outreach (DRY-RUN)
- `sources/` — duckduckgo_source (primary), reddit_source (blocked 403 sometimes)
- `config/{countries.json, niches.json}`
- `scripts/optin_server.py` — consent-based opt-in funnel
- `scripts/dashboard_v2.py` — metrics

## Commands (no send without approval)
```bash
python3 -m core.pipeline discover --niches plumbing roofing --countries US GB
python3 -m core.pipeline verify-businesses
python3 -m core.pipeline match
python3 -m core.pipeline outreach        # dry-run preview
```

## Rules
- Same-city matching only (match_score combines niche + verification + freshness)
- Intent signals older than 7 days → archived, needs_review for unclear city
- NOTHING sends BEFORE "APPROVE SEND"
- Never email guessed addresses; MX + junk filter required

## Data files
- `data/leads.json`, `data/businesses.json`, `data/deals.json` — unified
- `data/{buyer_leads,scan_results,deals}.json` — legacy (still present)

## Server startup
```bash
python3 scripts/optin_server.py 12001 &
python3 -m http.server 12000 --directory ../dashboard &
```

## Secrets (IN .env, gitignored)
- Gmail (`GMAIL_USER`, `GMAIL_APP_PASSWORD`)
- (Optional) TAVILY_API_KEY, GOOGLE_PLACES_API_KEY

## Workflow for agent
1. Discover / verify / match / dry-run
2. Show proposals + sources + verification status
3. Only on "APPROVE SEND" user approval, send
4. Update dashboard_v2.py in same run

## Known limitations
- Reddit API returns 403 sometimes; use duckduckgo fallback (common.ddg)
- Overpass blocked from this sandbox; not active in adapters
- Playwright browsers must be installed per-user when using form filler
