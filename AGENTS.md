# Project Memory — ProConnect Hub Marketplace System

## ⚠️ READ THIS FIRST — DO NOT re-explore the codebase or re-run setup
Everything is already built and running. Just read this file and continue.

## GitHub Repository
- Repo: https://github.com/Issamonge/proconnect-hub
- Clone: `git clone https://github.com/Issamonge/proconnect-hub.git`
- This repo contains all scripts, code, and documentation.
- Data files (business lists, leads, deals) are in .gitignore — they live in the workspace only.

## Current State (as of 2026-08-19)

### WORKSPACE REBUILT. Old data/ was gitignored and lost. Pipeline rebuilt from scratch:
- 224 businesses in data/scan_results.json (via scripts/rebuild_businesses.py — DuckDuckGo scraping; Overpass API is BLOCKED from this sandbox, all mirrors unreachable)
- 17 real buyers/renters in data/buyer_leads.json (found via Tavily MCP search, added by scripts/add_buyers.py)
- 90 deals in data/deals.json ($2,250 potential revenue) — buyers re-matched to LOCAL businesses
- 23 deal offer emails SENT to businesses (Gmail credentials in .env — working)
- scripts/find_businesses_for_buyers.py — finds businesses in buyer cities via DDG
- Auto-replyer running in watch mode (checks Gmail every 5 min, auto-responds)
- Dashboard server: `python3 -m http.server 12000 --directory dashboard` (running)
- Marketplace server: `python3 scripts/marketplace_leads.py serve` on 12001 (running)
- Data quality note: business names come from DDG SEO titles; emails scraped from websites (only ~6/14 matched sellers had findable emails). Better business source = Google Places API key in .env

### Previous State (2026-08-17, old workspace — data lost):
- Old pipeline had: 139 businesses, 28 buyers, 86 deals, 34 lead offer emails sent

### System is OPERATIONAL. Do NOT restart servers unless dead.

### Deployed URLs (permanent on Vercel):
- Dashboard: https://deploy-nine-kappa-58.vercel.app
- Marketplace: https://marketplace-nu-peach.vercel.app
- Landing: https://landingdeploy-ruddy.vercel.app

### Running Services:
```bash
bash scripts/start_servers.sh  # starts dashboard(12000), auto-replyer, keep-alive
python3 scripts/marketplace_leads.py serve &  # marketplace lead server on 12001
```

### Pipeline Stats:
- 139 businesses in database (sellers)
- 28 real buyers/renters found on Reddit
- 86 deals created ($25 each = $2,150 potential revenue)
- 34 lead offer emails sent to businesses
- 0 replies so far (emails just sent)
- Auto-replyer running 24/7 (checks email every 5 min, auto-responds)

### Revenue: $0 actual / $2,150 potential

### Key Files:
- data/scan_results.json — 139 businesses (sellers)
- data/buyer_leads.json — 28 buyers/renters found on internet
- data/deals.json — 86 deals
- data/sent_lead_offers.json — 34 lead offer emails sent
- data/marketplace_leads.json — leads from marketplace website
- data/call_results.json — 14 Bland AI calls (all voicemail/no answer)

### Key Scripts:
- scripts/buyer_finder.py — finds buyers on internet (uses Tavily search)
- scripts/deal_closer.py — matches buyers with businesses, creates deals
- scripts/lead_offer_emailer.py — emails businesses offering customer leads
- scripts/marketplace_leads.py — marketplace lead collection server
- scripts/auto_replyer.py — AI auto-responds to business emails 24/7
- scripts/reply_handler.py — intent detection + response templates (includes lead offer responses)
- scripts/craigslist_finder.py — Craigslist buyer search (blocked by CL, use buyer_finder instead)
- scripts/dashboard.py — generates dashboard HTML
- scripts/bland_client.py — Bland AI voice calls (OUT OF CREDITS)

### Credentials (in .env):
- GMAIL_USER / GMAIL_APP_PASSWORD — Gmail for sending/receiving
- BLAND_API_KEY — Bland AI (insufficient balance)
- Vercel token: stored in .env as VERCEL_TOKEN
- GitHub: Issamonge (write token configured)
- PayPal: ihakizimana11@gmail.com
- Crypto (BEP20): 0x27e16d0df86a051e1b14c0f5b90db76d74fd0704

### User Context:
- User does NOT speak English — all communication must be simple and clear
- User wants automated money-making system with ZERO investment
- User is frustrated by no revenue yet
- User HATES waiting for me to re-explore/re-setup each session
- Business model: Find buyers online → match with businesses → charge businesses $25/lead

### What To Do When User Returns:
1. Check for business email replies: `python3 scripts/auto_replyer.py --once`
2. Check deal stats: `python3 scripts/deal_closer.py --stats`
3. If user says "find more buyers" → use Tavily search for new Reddit posts
4. If user says "find more businesses" → search for businesses with emails in buyer cities
5. If user says "check replies" → run auto_replyer --once and show results
6. Do NOT re-run setup, re-deploy, or re-explain unless something is broken

### Deploy:
```bash
python3 scripts/dashboard.py && cp dashboard/index.html public/deploy/index.html
source .env && npx --yes vercel deploy public/deploy --prod --token $VERCEL_TOKEN --yes
```

### Known Issues:
- Bland AI out of credits (can't make voice calls)
- Reddit API requires approval now (blocked, use web search instead)
- Craigslist blocks automated requests
- Some business matches are cross-city (need more local businesses)
