"""
LEAD DATABASE
=============
Stores all call results in a simple SQLite database.
Every call the AI agent handles gets saved here.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "leads.db"


def init_db():
    """Create the database tables if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id TEXT UNIQUE,
            timestamp TEXT,
            customer_name TEXT,
            customer_phone TEXT,
            customer_email TEXT,
            product_interest TEXT,
            budget TEXT,
            timeline TEXT,
            qualified INTEGER DEFAULT 0,
            meeting_booked INTEGER DEFAULT 0,
            meeting_time TEXT,
            call_outcome TEXT,
            call_summary TEXT,
            transcript TEXT,
            recording_url TEXT,
            duration_seconds INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS follow_ups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id TEXT,
            follow_up_date TEXT,
            status TEXT DEFAULT 'pending',
            message_sent TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_call(call_data):
    """Save a call result to the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    analysis = call_data.get("analysis", {})
    summary = analysis.get("summary", "")
    structured = analysis.get("structuredData", {})

    c.execute("""
        INSERT OR REPLACE INTO calls (
            call_id, timestamp, customer_name, customer_phone, customer_email,
            product_interest, budget, timeline, qualified, meeting_booked,
            meeting_time, call_outcome, call_summary, transcript, recording_url,
            duration_seconds
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        call_data.get("id", ""),
        datetime.now().isoformat(),
        structured.get("customer_name", ""),
        structured.get("customer_phone", call_data.get("customer", {}).get("number", "")),
        structured.get("customer_email", ""),
        structured.get("product_interest", ""),
        structured.get("budget", ""),
        structured.get("timeline", ""),
        1 if structured.get("qualified") else 0,
        1 if structured.get("meeting_booked") else 0,
        structured.get("meeting_time", ""),
        structured.get("call_outcome", ""),
        summary,
        json.dumps(call_data.get("transcript", "")),
        call_data.get("recordingUrl", call_data.get("artifact", {}).get("recordingUrl", "")),
        call_data.get("durationSeconds", 0),
    ))

    conn.commit()
    conn.close()
    return structured


def get_all_leads():
    """Get all leads from the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM calls ORDER BY timestamp DESC")
    columns = [desc[0] for desc in c.description]
    leads = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    return leads


def get_qualified_leads():
    """Get only qualified leads that need follow-up."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM calls WHERE qualified = 1 AND meeting_booked = 0 ORDER BY timestamp DESC")
    columns = [desc[0] for desc in c.description]
    leads = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    return leads


if __name__ == "__main__":
    init_db()
    print("Database initialized at:", DB_PATH)
    leads = get_all_leads()
    print(f"Total leads in database: {len(leads)}")
