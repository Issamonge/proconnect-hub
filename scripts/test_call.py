"""
MAKE A TEST CALL
================
Make a test call to your AI voice agent to check it works.

Before running:
1. Create the agent:  python3 scripts/create_agent.py
2. Buy a phone number in Vapi dashboard
3. Set VAPI_ASSISTANT_ID and VAPI_PHONE_NUMBER_ID in .env

Usage:
  python3 scripts/test_call.py +12345678900   (call this number)
  python3 scripts/test_call.py                 (shows instructions)
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID", "")
VAPI_PHONE_NUMBER_ID = os.getenv("VAPI_PHONE_NUMBER_ID", "")


def make_test_call(target_number):
    """Make a test call to a phone number using the AI agent."""
    if not all([VAPI_API_KEY, VAPI_ASSISTANT_ID, VAPI_PHONE_NUMBER_ID]):
        print("ERROR: Missing configuration.")
        print("Set these in your .env file:")
        print("  VAPI_API_KEY")
        print("  VAPI_ASSISTANT_ID")
        print("  VAPI_PHONE_NUMBER_ID")
        return

    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "assistantId": VAPI_ASSISTANT_ID,
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": target_number,
        },
    }

    print(f"Making test call to {target_number}...")
    print("The AI agent will call this number and start talking.")
    print()

    response = requests.post(
        "https://api.vapi.ai/call",
        headers=headers,
        json=payload,
        timeout=15,
    )

    if response.status_code in (200, 201):
        data = response.json()
        print("SUCCESS! Call started.")
        print(f"Call ID: {data.get('id', 'unknown')}")
        print()
        print("Listen to the call. The AI should:")
        print("  1. Say hello and ask how it can help")
        print("  2. Ask qualifying questions")
        print("  3. Try to book a meeting")
        print()
        print("Check call results in your database:")
        print("  python3 scripts/lead_database.py")
    else:
        print(f"ERROR: {response.status_code}")
        print(response.text)


def main():
    print("=" * 50)
    print("  AI VOICE AGENT - TEST CALL")
    print("=" * 50)
    print()

    if len(sys.argv) < 2:
        print("HOW TO TEST:")
        print()
        print("1. First, create your AI agent:")
        print("   python3 scripts/create_agent.py")
        print()
        print("2. Buy a phone number in Vapi dashboard")
        print("   https://dashboard.vapi.ai")
        print()
        print("3. Set VAPI_PHONE_NUMBER_ID in your .env file")
        print()
        print("4. Make a test call:")
        print("   python3 scripts/test_call.py +12345678900")
        print()
        print("Replace +12345678900 with YOUR phone number (with country code).")
        return

    target = sys.argv[1]
    if not target.startswith("+"):
        print("ERROR: Phone number must start with country code, e.g. +1 for USA, +44 for UK")
        return

    make_test_call(target)


if __name__ == "__main__":
    main()
