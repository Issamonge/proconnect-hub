# Setup Guide - AI Voice Agent

This guide helps you set up your AI voice agent step by step.
I will help you with each step. Just ask me when you have a question.

## Step 1: Get a Vapi.ai Account (5 minutes)

1. Go to https://vapi.ai
2. Click "Sign Up"
3. Create an account (email and password)
4. Go to the dashboard
5. Find your API key (look for "API Keys" or "Settings")
6. Copy your API key

## Step 2: Put Your API Key In The Project

1. Copy the `.env.example` file to `.env`
2. Open the `.env` file
3. Find the line: `VAPI_API_KEY=your_vapi_api_key_here`
4. Replace `your_vapi_api_key_here` with your real API key
5. Save the file

## Step 3: Tell Me About Your Business

I need to know:
- What is your business name?
- What are you selling? (product or service)
- How much does it cost?
- What questions do customers usually ask?

I will put these answers in the `.env` file for you.
The AI agent will use this information to answer customer questions.

## Step 4: Create The AI Agent

Run this command:

```
python3 scripts/create_agent.py
```

This creates your AI voice agent on Vapi. It will give you an "Assistant ID".
Save that ID in your `.env` file as `VAPI_ASSISTANT_ID`.

## Step 5: Buy A Phone Number

1. Go to your Vapi dashboard
2. Find "Phone Numbers"
3. Buy a phone number (about $1/month)
4. Copy the phone number ID
5. Put it in your `.env` file as `VAPI_PHONE_NUMBER_ID`

## Step 6: Start The Webhook Server

The webhook server receives call results so we can save leads.

Run these TWO commands in SEPARATE terminals:

Terminal 1 (start the server):
```
python3 scripts/webhook_server.py
```

Terminal 2 (make it public - install ngrok from https://ngrok.com):
```
ngrok http 8000
```

Ngrok will give you a public URL like `https://abc123.ngrok.app`.
Copy that URL and:
1. Put it in your `.env` file as `VAPI_SERVER_URL`
2. In your Vapi dashboard, set the webhook URL to:
   `https://abc123.ngrok.app/webhook`

## Step 7: Test The Call

Make a test call to yourself:

```
python3 scripts/test_call.py +12345678900
```

Replace `+12345678900` with your real phone number (with country code).

Your phone will ring. The AI will answer and start talking in English!
You can talk to it and test how it handles questions.

## Step 8: View Your Leads

After calls come in, you can see all your leads:

```
python3 scripts/lead_database.py
```

Or open the web view:
```
Go to http://localhost:8000/leads in your browser
```

---

## What The AI Agent Does On Calls

1. Answers the phone in perfect English
2. Says: "Hello! Thank you for calling [your business]. How can I help?"
3. Asks what the customer needs
4. Asks 2-3 qualifying questions (budget, timeline, what they want)
5. Answers questions about your product/service
6. Tries to book a meeting on your calendar
7. Says goodbye
8. You get a notification with all the lead details

## You Never Have To Speak English!

The AI handles ALL the talking. You only see the results:
- Customer name and phone number
- What they wanted to buy
- Their budget and timeline
- Whether they are qualified
- Whether a meeting was booked

---

## Questions? Ask Me!

If you get stuck on any step, just tell me:
- Which step you are on
- What happened (or what error you saw)
- I will help you fix it
