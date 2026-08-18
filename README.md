# AI Deal-Making System - Search, Call & Close

A complete system that searches the internet for leads, has an AI voice agent call them in English, qualifies them, and closes deals — without you ever speaking English.

## What This System Does

```
STEP 1: SEARCH
  System searches the internet for leads
  (local businesses, websites, contact info)
         ↓
STEP 2: CALL
  AI voice agent calls each lead in perfect English
  Introduces your service, asks qualifying questions
         ↓
STEP 3: QUALIFY
  AI asks about budget, timeline, needs
  AI answers questions about your product
         ↓
STEP 4: CLOSE
  Simple deals → AI sends payment link via SMS
  Custom deals → AI books a meeting on your calendar
         ↓
STEP 5: FOLLOW UP
  System sends SMS follow-ups to interested leads
  You get notified (Telegram) with all lead details
         ↓
STEP 6: REPORT
  You see all leads, qualified leads, closed deals
  Money comes to your Stripe/PayPal/Gumroad account
```

## How To Run It

### Find leads only (no calls yet):
```
python3 scripts/pipeline.py --find-only --niche plumber --location "Chicago, IL"
```

### Full pipeline (find + call + close):
```
python3 scripts/pipeline.py --niche plumber --location "Chicago, IL"
```

### Dry run (find leads, show what would be called, no actual calls):
```
python3 scripts/pipeline.py --dry-run --niche dentist --location "Los Angeles, CA"
```

### Just search for leads:
```
python3 scripts/lead_finder.py
```

### Make a single test call:
```
python3 scripts/outbound_caller.py --test +12345678900
```

## Files In This Project

| File | What it does |
|------|-------------|
| `scripts/pipeline.py` | **MAIN** - runs the full system (search → call → close) |
| `scripts/lead_finder.py` | Searches the net for leads (Overpass, Google, web search) |
| `scripts/outbound_caller.py` | AI calls leads automatically |
| `scripts/create_agent.py` | Creates the AI voice agent on Vapi |
| `scripts/webhook_server.py` | Receives call results, triggers deal closing |
| `scripts/lead_database.py` | Stores all leads and call results |
| `scripts/deal_closer.py` | Closes deals (sends payment links, books meetings) |
| `scripts/sms_followup.py` | Sends SMS follow-ups to leads |
| `scripts/notifications.py` | Sends you notifications (Telegram) |
| `scripts/test_call.py` | Makes a test call to check it works |
| `config/vapi_agent.json` | The AI brain (script, questions, call flow) |

## Cost

| Item | Cost |
|------|------|
| Lead search | $0 (free APIs: Overpass, web search) |
| Vapi.ai calls | ~$0.10-0.15 per minute |
| Phone number | ~$1/month |
| SMS (Twilio) | ~$0.0079 per message |
| Google Calendar | Free |
| **Total to start** | **Under $5** |

## What You Need To Set Up

See `SETUP_GUIDE.md` and `PROOF_PLAN.md` for step-by-step instructions.

## MCP Integration

The system supports MCP (Model Context Protocol) for connecting to external tools:
- See `config/mcp.json` for available MCP servers
- Connects to: filesystem, web fetch, Gmail, memory, SQLite, time
- Add more later: Stripe, calendar, Slack, social media

## Reply Handler (No English Needed)

When businesses reply to your emails, you don't need to write English:
```
python3 scripts/reply_handler.py
```
Paste their reply → get the perfect English response → copy-paste and send.
