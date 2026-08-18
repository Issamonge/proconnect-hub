"""
CREATE AI VOICE AGENT ON VAPI
================================
Run this script ONCE to create your AI voice agent on Vapi.ai.

Before running:
1. Sign up at https://vapi.ai
2. Get your API key from the dashboard
3. Put your API key in the .env file (copy .env.example to .env)
4. Run: python3 scripts/create_agent.py

This will create the AI voice agent that answers your calls in perfect English.
"""
import os
import json
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")
if not VAPI_API_KEY or VAPI_API_KEY == "your_vapi_api_key_here":
    print("ERROR: You need to set VAPI_API_KEY in your .env file.")
    print("1. Copy .env.example to .env")
    print("2. Sign up at https://vapi.ai")
    print("3. Put your API key in the .env file")
    sys.exit(1)

VAPI_BASE_URL = "https://api.vapi.ai"


def load_agent_config():
    """Load the agent config and fill in business details."""
    with open("config/vapi_agent.json", "r") as f:
        config = json.load(f)

    business_name = os.getenv("BUSINESS_NAME", "Your Business")
    product_name = os.getenv("PRODUCT_NAME", "our services")
    product_price = os.getenv("PRODUCT_PRICE", "varies")
    product_description = os.getenv("PRODUCT_DESCRIPTION", "Please ask us for details.")
    knowledge_base = os.getenv("KNOWLEDGE_BASE", product_description)

    # Fill in the system prompt with business details
    system_content = config["model"]["messages"][0]["content"]
    system_content = system_content.replace("{{business_name}}", business_name)
    system_content = system_content.replace("{{product_name}}", product_name)
    system_content = system_content.replace("{{product_price}}", product_price)
    system_content = system_content.replace("{{product_description}}", product_description)
    system_content = system_content.replace("{{knowledge_base}}", knowledge_base)
    config["model"]["messages"][0]["content"] = system_content

    config["firstMessage"] = config["firstMessage"].replace("{{business_name}}", business_name)
    config["voicemailMessage"] = config["voicemailMessage"].replace("{{business_name}}", business_name)
    config["name"] = f"{business_name} AI Assistant"

    return config


def create_agent(config):
    """Create the assistant on Vapi."""
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.post(f"{VAPI_BASE_URL}/assistant", headers=headers, json=config)
    if response.status_code in (200, 201):
        data = response.json()
        print("SUCCESS! AI voice agent created.")
        print(f"Assistant ID: {data['id']}")
        print()
        print("NEXT STEPS:")
        print("1. Save this Assistant ID in your .env file as VAPI_ASSISTANT_ID")
        print("2. Buy a phone number in the Vapi dashboard")
        print("3. Run the webhook server: python3 scripts/webhook_server.py")
        print("4. Make a test call: python3 scripts/test_call.py")
        return data
    else:
        print(f"ERROR creating agent: {response.status_code}")
        print(response.text)
        return None


def main():
    print("=" * 50)
    print("  CREATING AI VOICE AGENT ON VAPI")
    print("=" * 50)
    print()

    config = load_agent_config()
    print(f"Business: {config['name']}")
    print()

    confirm = input("Create this agent on Vapi now? (yes/no): ")
    if confirm.lower() not in ("yes", "y"):
        print("Cancelled. No agent created.")
        return

    result = create_agent(config)
    if result:
        # Save the assistant ID to a file for easy reference
        with open("config/assistant_id.txt", "w") as f:
            f.write(result["id"])
        print()
        print("Assistant ID saved to config/assistant_id.txt")


if __name__ == "__main__":
    main()
