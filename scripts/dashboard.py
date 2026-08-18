"""
DASHBOARD GENERATOR
===================
Generates a live HTML dashboard showing the system's performance:
  - Total leads found
  - Total emails sent
  - Emails sent per day (chart)
  - Leads by niche
  - Leads by city
  - Recent activity log
  - Recent sent emails

The dashboard reads data files and generates dashboard/index.html.
Run this after each daily run to update the dashboard.

USAGE:
  python3 scripts/dashboard.py
"""
import os
import sys
import json
import logging
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

BUSINESS_NAME = os.getenv("BUSINESS_NAME", "AI Pro Assist")
WHATSAPP_LINK = os.getenv("WHATSAPP_LINK", "")
BUSINESS_EMAIL = os.getenv("BUSINESS_EMAIL", "")


def load_json(path, default=None):
    """Load a JSON file, return default if it doesn't exist."""
    if default is None:
        default = []
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return default
    return default


def get_stats():
    """Collect all stats from the data files."""
    stats = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_leads": 0,
        "total_emails_sent": 0,
        "total_emails_extracted": 0,
        "leads_by_niche": {},
        "leads_by_city": {},
        "emails_by_day": {},
        "emails_by_niche": {},
        "recent_sent": [],
        "recent_log": [],
    }

    # Leads found
    scan = load_json(os.path.join(DATA_DIR, "scan_results.json"))
    stats["total_leads"] = len(scan)
    stats["leads_by_niche"] = dict(Counter(l.get("scan_niche", l.get("niche", "unknown")) for l in scan))
    stats["leads_by_city"] = dict(Counter(l.get("scan_city", l.get("location", "unknown")) for l in scan))

    # Extracted emails
    extracted = load_json(os.path.join(DATA_DIR, "extracted_emails.json"))
    stats["total_emails_extracted"] = len(extracted)

    # Sent emails
    sent = load_json(os.path.join(DATA_DIR, "sent_emails.json"))
    stats["total_emails_sent"] = len(sent)
    stats["emails_by_niche"] = dict(Counter(s.get("niche", "unknown") for s in sent))

    # Auto-replied emails (deals being closed)
    auto_replied = load_json(os.path.join(DATA_DIR, "auto_replied.json"))
    stats["total_auto_replied"] = len(auto_replied)
    stats["deals_ready"] = sum(1 for r in auto_replied if r.get("intent") in ["interested", "yes", "how_much", "demo"])
    stats["recent_replies"] = sorted(auto_replied, key=lambda x: x.get("replied_at", ""), reverse=True)[:10]

    # Emails by day
    emails_by_day = Counter()
    for s in sent:
        date = s.get("sent_at", "")[:10]
        if date:
            emails_by_day[date] += 1
    stats["emails_by_day"] = dict(sorted(emails_by_day.items()))

    # Recent sent (last 20)
    stats["recent_sent"] = sorted(sent, key=lambda x: x.get("sent_at", ""), reverse=True)[:20]

    # Call results
    calls = load_json(os.path.join(DATA_DIR, "call_results.json"))
    stats["total_calls"] = len(calls)
    stats["calls_interested"] = sum(1 for c in calls if c.get("result") == "interested")
    stats["calls_voicemail"] = sum(1 for c in calls if c.get("result") == "voicemail")
    stats["calls_no_answer"] = sum(1 for c in calls if c.get("result") == "no_answer")
    stats["calls_maybe"] = sum(1 for c in calls if c.get("result") == "maybe")
    stats["calls_not_interested"] = sum(1 for c in calls if c.get("result") == "not_interested")
    stats["recent_calls"] = sorted(calls, key=lambda x: x.get("called_at", ""), reverse=True)[:15]

    # Payments
    payments = load_json(os.path.join(DATA_DIR, "payments.json"))
    stats["total_invoices"] = len(payments)
    stats["paid_invoices"] = sum(1 for p in payments if p.get("status") == "paid")
    stats["pending_invoices"] = sum(1 for p in payments if p.get("status") == "pending")
    stats["revenue"] = sum(p.get("amount", 0) for p in payments if p.get("status") == "paid")
    stats["pending_revenue"] = sum(p.get("amount", 0) for p in payments if p.get("status") == "pending")
    stats["recent_payments"] = sorted(payments, key=lambda x: x.get("created_at", ""), reverse=True)[:10]

    # Marketplace leads
    mleads = load_json(os.path.join(DATA_DIR, "marketplace_leads.json"))
    stats["marketplace_total"] = len(mleads)
    stats["marketplace_buyers"] = sum(1 for l in mleads if l.get("type") == "buyer")
    stats["marketplace_sellers"] = sum(1 for l in mleads if l.get("type") == "seller")
    stats["marketplace_renters"] = sum(1 for l in mleads if l.get("type") == "renter")
    stats["marketplace_recent"] = sorted(mleads, key=lambda x: x.get("received_at", ""), reverse=True)[:10]

    # Buyer leads found on internet (Reddit etc.)
    buyer_leads = load_json(os.path.join(DATA_DIR, "buyer_leads.json"))
    stats["internet_buyers"] = len(buyer_leads)
    stats["internet_matched"] = sum(1 for l in buyer_leads if l.get("status") == "matched")

    # Deals
    deals = load_json(os.path.join(DATA_DIR, "deals.json"))
    stats["total_deals"] = len(deals)
    stats["deals_pending"] = sum(1 for d in deals if d.get("status") in ("pending_contact",))
    stats["deals_emailed"] = sum(1 for d in deals if d.get("status") == "email_sent")
    stats["deals_paid"] = sum(1 for d in deals if d.get("status") == "paid")
    stats["potential_revenue"] = len(deals) * 25
    stats["actual_revenue_deals"] = sum(1 for d in deals if d.get("status") == "paid") * 25
    stats["recent_deals"] = sorted(deals, key=lambda x: x.get("created_at", ""), reverse=True)[:15]

    # Lead offer emails sent
    sent_offers = load_json(os.path.join(DATA_DIR, "sent_lead_offers.json"))
    stats["lead_emails_sent"] = len(sent_offers)

    # Recent log
    log_file = os.path.join(DATA_DIR, "daily_runner.log")
    if os.path.exists(log_file):
        with open(log_file) as f:
            lines = f.readlines()
        stats["recent_log"] = [l.strip() for l in lines[-30:] if l.strip()]

    return stats


def generate_dashboard():
    """Generate the HTML dashboard."""
    stats = get_stats()

    os.makedirs(DASHBOARD_DIR, exist_ok=True)

    # Build charts data
    emails_by_day_labels = list(stats["emails_by_day"].keys())
    emails_by_day_values = list(stats["emails_by_day"].values())

    niche_labels = list(stats["leads_by_niche"].keys())
    niche_values = list(stats["leads_by_niche"].values())

    # Recent sent table rows
    sent_rows = ""
    for s in stats["recent_sent"]:
        sent_rows += f"""
            <tr>
                <td>{s.get("sent_at", "")[:16]}</td>
                <td>{s.get("to", "")}</td>
                <td>{s.get("niche", "")}</td>
                <td>{s.get("subject", "")[:40]}</td>
            </tr>
        """

    # Auto-replied table rows
    reply_rows = ""
    for r in stats.get("recent_replies", []):
        intent_badge = r.get("intent", "question")
        badge_color = "#22c55e" if intent_badge in ["interested", "yes", "how_much", "demo"] else "#64748b"
        reply_rows += f"""
            <tr>
                <td>{r.get("replied_at", "")[:16]}</td>
                <td>{r.get("from_email", "")}</td>
                <td><span style="background:{badge_color};color:white;padding:2px 8px;border-radius:8px;font-size:11px;">{intent_badge}</span></td>
                <td>{r.get("body_preview", "")[:50]}...</td>
            </tr>
        """

    # Recent log
    log_lines = "\n".join(stats["recent_log"]) if stats["recent_log"] else "No activity yet."

    # Build call table rows
    call_rows = ""
    for c in stats.get("recent_calls", []):
        result_icon = {"interested": "🎯", "voicemail": "📞", "no_answer": "❌", "maybe": "🤔", "not_interested": "🚫"}.get(c.get("result", ""), "⏳")
        dur = c.get("duration") or 0
        call_rows += f'<tr><td>{c.get("called_at","")[:16]}</td><td>{c.get("lead_name","")[:40]}</td><td>{c.get("niche","")}</td><td>{result_icon} {c.get("result","pending")}</td><td>{dur:.0f}s</td></tr>\n'

    # Build payment table rows
    payment_rows = ""
    for p in stats.get("recent_payments", []):
        status_icon = "✅" if p.get("status") == "paid" else "⏳"
        payment_rows += f'<tr><td>{p.get("invoice_id","")}</td><td>{p.get("lead_name","")[:40]}</td><td>${p.get("amount",0)}</td><td>{status_icon} {p.get("status","")}</td></tr>\n'

    # Build marketplace lead rows
    mkt_rows = ""
    type_icons = {"buyer": "🔍", "seller": "📈", "renter": "🏠"}
    for l in stats.get("marketplace_recent", []):
        ltype = l.get("type", "")
        icon = type_icons.get(ltype, "📋")
        detail = l.get("service") or l.get("business") or l.get("propertyType") or ""
        mkt_rows += f'<tr><td>{l.get("received_at","")[:16]}</td><td>{icon} {ltype}</td><td>{l.get("name","")[:30]}</td><td>{detail}</td><td>{l.get("city","")}</td></tr>\n'

    # Build deal rows
    deal_rows = ""
    for d in stats.get("recent_deals", []):
        status_icon = {"pending_contact": "⏳", "email_sent": "📧", "paid": "✅"}.get(d.get("status",""), "⏳")
        deal_rows += f'<tr><td>{d.get("lead_title","")[:35]}</td><td>{d.get("seller_name","")[:30]}</td><td>{d.get("seller_phone","")}</td><td>{d.get("lead_location","")}</td><td>{status_icon} {d.get("status","")}</td><td>${d.get("lead_fee",25)}</td></tr>\n'

    # Niche breakdown bars
    max_niche = max(niche_values) if niche_values else 1
    niche_bars = ""
    for niche, count in zip(niche_labels, niche_values):
        pct = int(count / max_niche * 100)
        niche_bars += f"""
            <div class="bar-row">
                <span class="bar-label">{niche}</span>
                <div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>
                <span class="bar-value">{count}</span>
            </div>
        """

    # City breakdown
    city_items = ""
    for city, count in sorted(stats["leads_by_city"].items(), key=lambda x: -x[1])[:15]:
        city_items += f"<div class='city-item'><span>{city}</span><b>{count}</b></div>\n"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <title>{BUSINESS_NAME} — Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a; color: #e2e8f0; min-height: 100vh;
        }}
        .header {{
            background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 30px 40px;
            text-align: center;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 5px; }}
        .header p {{ color: #c7d2fe; font-size: 14px; }}
        .header .updated {{ color: #a5b4fc; font-size: 12px; margin-top: 8px; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 30px 20px; }}
        .stats-grid {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px; margin-bottom: 30px;
        }}
        .stat-card {{
            background: #1e293b; border-radius: 16px; padding: 25px; text-align: center;
            border: 1px solid #334155;
        }}
        .stat-card .icon {{ font-size: 32px; margin-bottom: 10px; }}
        .stat-card .number {{ font-size: 36px; font-weight: 700; color: #818cf8; }}
        .stat-card .label {{ font-size: 14px; color: #94a3b8; margin-top: 5px; }}
        .section {{
            background: #1e293b; border-radius: 16px; padding: 25px; margin-bottom: 25px;
            border: 1px solid #334155;
        }}
        .section h2 {{
            font-size: 18px; margin-bottom: 20px; color: #c084fc;
        }}
        .chart-container {{ position: relative; height: 250px; }}
        .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 25px; }}
        @media (max-width: 768px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ text-align: left; padding: 10px 12px; font-size: 13px; }}
        th {{ color: #94a3b8; border-bottom: 1px solid #334155; }}
        td {{ border-bottom: 1px solid #1e293b; color: #cbd5e1; }}
        tr:hover td {{ background: #334155; }}
        .bar-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }}
        .bar-label {{ width: 100px; font-size: 13px; color: #94a3b8; text-transform: capitalize; }}
        .bar-track {{ flex: 1; height: 22px; background: #334155; border-radius: 11px; overflow: hidden; }}
        .bar-fill {{ height: 100%; background: linear-gradient(90deg, #6366f1, #8b5cf6); border-radius: 11px; }}
        .bar-value {{ width: 30px; text-align: right; font-size: 13px; font-weight: 600; }}
        .city-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 8px; }}
        .city-item {{ display: flex; justify-content: space-between; padding: 8px 12px; background: #0f172a; border-radius: 8px; font-size: 13px; }}
        .city-item b {{ color: #818cf8; }}
        .log-box {{
            background: #0f172a; border-radius: 10px; padding: 15px; max-height: 300px;
            overflow-y: auto; font-family: 'Courier New', monospace; font-size: 12px;
            color: #64748b; line-height: 1.6;
        }}
        .footer {{
            text-align: center; padding: 20px; color: #475569; font-size: 13px;
        }}
        .footer a {{ color: #818cf8; text-decoration: none; }}
        .empty {{ color: #475569; font-style: italic; padding: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 {BUSINESS_NAME} Dashboard</h1>
        <p>AI Voice Assistant Business — Automated Lead System</p>
        <p class="updated">Last updated: {stats["generated_at"]} (auto-refreshes every 60s)</p>
    </div>

    <div class="container">
        <!-- Top stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="icon">🎯</div>
                <div class="number">{stats["total_leads"]}</div>
                <div class="label">Leads Found</div>
            </div>
            <div class="stat-card">
                <div class="icon">📧</div>
                <div class="number">{stats["total_emails_sent"]}</div>
                <div class="label">Emails Sent</div>
            </div>
            <div class="stat-card">
                <div class="icon">📬</div>
                <div class="number">{stats["total_emails_extracted"]}</div>
                <div class="label">Emails Extracted</div>
            </div>
            <div class="stat-card">
                <div class="icon">🤖</div>
                <div class="number">{stats["total_auto_replied"]}</div>
                <div class="label">AI Auto-Replied</div>
            </div>
            <div class="stat-card">
                <div class="icon">🔔</div>
                <div class="number">{stats["deals_ready"]}</div>
                <div class="label">Deals Ready</div>
            </div>
            <div class="stat-card">
                <div class="icon">🌍</div>
                <div class="number">{len(stats["leads_by_city"])}</div>
                <div class="label">Cities Covered</div>
            </div>
            <div class="stat-card">
                <div class="icon">📞</div>
                <div class="number">{stats["total_calls"]}</div>
                <div class="label">Voice Calls Made</div>
            </div>
            <div class="stat-card">
                <div class="icon">💰</div>
                <div class="number">${stats["revenue"]}</div>
                <div class="label">Revenue</div>
            </div>
            <div class="stat-card">
                <div class="icon">🏪</div>
                <div class="number">{stats["marketplace_total"]}</div>
                <div class="label">Marketplace Leads</div>
            </div>
            <div class="stat-card">
                <div class="icon">🤝</div>
                <div class="number">{stats["total_deals"]}</div>
                <div class="label">Active Deals</div>
            </div>
            <div class="stat-card">
                <div class="icon">💎</div>
                <div class="number">${stats["potential_revenue"]}</div>
                <div class="label">Potential Revenue</div>
            </div>
        </div>

        <!-- Emails per day chart -->
        <div class="section">
            <h2>📈 Emails Sent Per Day</h2>
            <div class="chart-container">
                <canvas id="emailsChart"></canvas>
            </div>
        </div>

        <div class="two-col">
            <!-- Leads by niche -->
            <div class="section">
                <h2>🔥 Leads by Niche</h2>
                {niche_bars if niche_bars else '<div class="empty">No leads yet</div>'}
            </div>

            <!-- Cities covered -->
            <div class="section">
                <h2>📍 Cities Covered</h2>
                <div class="city-grid">
                    {city_items if city_items else '<div class="empty">No cities yet</div>'}
                </div>
            </div>
        </div>

        <!-- Recent sent emails -->
        <div class="section">
            <h2>📤 Recently Sent Emails</h2>
            {f'<table><thead><tr><th>Date</th><th>To</th><th>Niche</th><th>Subject</th></tr></thead><tbody>{sent_rows}</tbody></table>' if sent_rows else '<div class="empty">No emails sent yet</div>'}
        </div>

        <!-- Auto-replied (deals being closed) -->
        <div class="section">
            <h2>🤖 AI Auto-Replied (Deals Being Closed)</h2>
            {f'<table><thead><tr><th>Date</th><th>From</th><th>Intent</th><th>Preview</th></tr></thead><tbody>{reply_rows}</tbody></table>' if reply_rows else '<div class="empty">No replies yet — businesses will reply in 2-3 days</div>'}
        </div>

        <!-- Voice calls -->
        <div class="section">
            <h2>📞 AI Voice Calls (Bland AI)</h2>
            <div class="call-summary" style="display:flex;gap:20px;margin-bottom:15px;flex-wrap:wrap;">
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">Total: <strong>{stats["total_calls"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">🎯 Interested: <strong>{stats["calls_interested"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">🤔 Maybe: <strong>{stats["calls_maybe"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">📞 Voicemail: <strong>{stats["calls_voicemail"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">❌ No Answer: <strong>{stats["calls_no_answer"]}</strong></div>
            </div>
            {f'<table><thead><tr><th>Date</th><th>Business</th><th>Niche</th><th>Result</th><th>Duration</th></tr></thead><tbody>{call_rows}</tbody></table>' if call_rows else '<div class="empty">No calls made yet</div>'}
        </div>

        <!-- Payments -->
        <div class="section">
            <h2>💰 Payments & Revenue</h2>
            <div class="call-summary" style="display:flex;gap:20px;margin-bottom:15px;flex-wrap:wrap;">
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">Invoices: <strong>{stats["total_invoices"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">⏳ Pending: <strong>{stats["pending_invoices"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">✅ Paid: <strong>{stats["paid_invoices"]}</strong></div>
                <div style="background:#065f46;padding:10px 20px;border-radius:8px;">💵 Revenue: <strong>${stats["revenue"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">📋 Pending $: <strong>${stats["pending_revenue"]}</strong></div>
            </div>
            {f'<table><thead><tr><th>Invoice</th><th>Lead</th><th>Amount</th><th>Status</th></tr></thead><tbody>{payment_rows}</tbody></table>' if payment_rows else '<div class="empty">No invoices yet — payments auto-generated when leads are interested</div>'}
        </div>

        <!-- Marketplace -->
        <div class="section">
            <h2>🏪 ProConnect Hub Marketplace</h2>
            <div class="call-summary" style="display:flex;gap:20px;margin-bottom:15px;flex-wrap:wrap;">
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">Total Leads: <strong>{stats["marketplace_total"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">🔍 Buyers: <strong>{stats["marketplace_buyers"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">📈 Sellers: <strong>{stats["marketplace_sellers"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">🏠 Renters: <strong>{stats["marketplace_renters"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;"><a href="https://marketplace-nu-peach.vercel.app" target="_blank" style="color:#6366f1;">🔗 Open Marketplace →</a></div>
            </div>
            {f'<table><thead><tr><th>Date</th><th>Type</th><th>Name</th><th>Service/Property</th><th>City</th></tr></thead><tbody>{mkt_rows}</tbody></table>' if mkt_rows else '<div class="empty">No marketplace leads yet — share your marketplace link to get buyer/seller/renter leads</div>'}
        </div>

        <!-- Deals -->
        <div class="section">
            <h2>🤝 Active Deals — Buyers Matched with Businesses</h2>
            <div class="call-summary" style="display:flex;gap:20px;margin-bottom:15px;flex-wrap:wrap;">
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">Total Deals: <strong>{stats["total_deals"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">⏳ Pending: <strong>{stats["deals_pending"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">📧 Emailed: <strong>{stats["deals_emailed"]}</strong></div>
                <div style="background:#1e293b;padding:10px 20px;border-radius:8px;">✅ Paid: <strong>{stats["deals_paid"]}</strong></div>
                <div style="background:#065f46;padding:10px 20px;border-radius:8px;">💎 Potential: <strong>${stats["potential_revenue"]}</strong></div>
            </div>
            <p style="color:#94a3b8;font-size:0.85em;margin-bottom:10px;">Found {stats["internet_buyers"]} real buyers/renters on Reddit, matched with businesses from your database. {stats["lead_emails_sent"]} lead offer emails sent to businesses. Auto-replyer is running 24/7 to handle responses.</p>
            {f'<table><thead><tr><th>Deal</th><th>Business</th><th>Phone</th><th>Lead Location</th><th>Status</th><th>Fee</th></tr></thead><tbody>{deal_rows}</tbody></table>' if deal_rows else '<div class="empty">No deals yet</div>'}
        </div>

        <!-- Activity log -->
        <div class="section">
            <h2>📋 Recent Activity Log</h2>
            <div class="log-box">{log_lines}</div>
        </div>
    </div>

    <div class="footer">
        <p>{BUSINESS_NAME} — Automated Lead System</p>
        <p>📧 <a href="mailto:{BUSINESS_EMAIL}">{BUSINESS_EMAIL}</a>
        {' | 💬 <a href="' + WHATSAPP_LINK + '">WhatsApp</a>' if WHATSAPP_LINK else ''}</p>
    </div>

    <script>
        const ctx = document.getElementById('emailsChart');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(emails_by_day_labels)},
                datasets: [{{
                    label: 'Emails Sent',
                    data: {json.dumps(emails_by_day_values)},
                    backgroundColor: '#6366f1',
                    borderRadius: 8,
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ beginAtZero: true, ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }} }},
                    x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e293b' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
    """

    output_path = os.path.join(DASHBOARD_DIR, "index.html")
    with open(output_path, "w") as f:
        f.write(html)

    # Also copy to public/ for the combined site
    public_dir = os.path.join(BASE_DIR, "public")
    os.makedirs(public_dir, exist_ok=True)
    with open(os.path.join(public_dir, "dashboard.html"), "w") as f:
        f.write(html)

    logger.info(f"Dashboard generated: {output_path}")
    logger.info(f"  Leads: {stats['total_leads']} | Sent: {stats['total_emails_sent']} | Cities: {len(stats['leads_by_city'])}")
    return output_path


def main():
    print("=" * 60)
    print("  📊 DASHBOARD GENERATOR")
    print("=" * 60)
    generate_dashboard()
    print()
    print("Dashboard saved to: dashboard/index.html")
    print("Run a local server to view:")
    print("  python3 -m http.server 12000 --directory dashboard")


if __name__ == "__main__":
    main()
