
import os
import json
import asyncio
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from subscriptions import fetch_subscriptions, save_subscriptions, SUBSCRIPTIONS_FILE
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

# To run the app on the port specified in .env, use:
#   uvicorn main:app --reload --port $(grep FASTAPI_PORT .env | cut -d '=' -f2)

load_dotenv()

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 300))  # seconds, default 5 min
CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI")
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

print("CLIENT_ID:", CLIENT_ID)

app = FastAPI(
    title="YouTube Subscriptions Monitor",
    version="1.0.2"
)

@app.on_event("startup")
async def start_monitor():
    asyncio.create_task(monitor_subscriptions())

async def monitor_subscriptions():
    prev_subs = None
    prev_subs_dict = {}
    if os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE) as f:
            prev_subs = json.load(f)
            prev_subs_dict = {s["channelId"]: s for s in prev_subs}
    while True:
        try:
            current_subs = fetch_subscriptions()
            current_subs_dict = {s["channelId"]: s for s in current_subs}
            if prev_subs is not None:
                prev_ids = set(prev_subs_dict.keys())
                curr_ids = set(current_subs_dict.keys())
                added_ids = curr_ids - prev_ids
                removed_ids = prev_ids - curr_ids
                added = [current_subs_dict[cid] for cid in added_ids]
                removed = [prev_subs_dict[cid] for cid in removed_ids]
                if added or removed:
                    await notify_webhook(added, removed)
            save_subscriptions(current_subs)
            prev_subs = current_subs
            prev_subs_dict = current_subs_dict
        except Exception as e:
            print(f"Error monitoring subscriptions: {e}")
        await asyncio.sleep(POLL_INTERVAL)

async def notify_webhook(added, removed):
    if not WEBHOOK_URL:
        print("No webhook URL set.")
        return
    content = ""
    if added:
        content += f"Added: {[s['title'] for s in added]}\n"
    if removed:
        content += f"Removed: {[s['title'] for s in removed]}\n"
    data = {"content": content.strip()}
    async with httpx.AsyncClient() as client:
        await client.post(WEBHOOK_URL, json=data)

@app.get("/")
def root():
    return {"status": "YouTube Subscriptions Monitor is running"}


# Endpoint to view subscriptions and count
@app.get("/subscriptions")
def get_subscriptions():
    try:
        with open(SUBSCRIPTIONS_FILE) as f:
            subs = json.load(f)
        return {
            "count": len(subs),
            "subscriptions": subs
        }
    except Exception as e:
        return {"error": str(e)}
    
# Endpoint to send a test message to the webhook
@app.post("/test-webhook")
async def test_webhook():
    if not WEBHOOK_URL:
        return {"error": "No webhook URL set."}
    data = {"content": "This is a test notification from the YouTube Subscriptions Monitor."}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(WEBHOOK_URL, json=data)
        return {"status": "Test message sent.", "webhook_response_status": resp.status_code}
    except Exception as e:
        return {"error": str(e)}

# --- OAuth2 Endpoints ---
@app.get("/authorize")
def authorize():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
    return RedirectResponse(auth_url)

@app.get("/oauth2callback")
def oauth2callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "No code provided"}
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    # Save credentials for later use
    with open("token.json", "w") as token:
        token.write(creds.to_json())
    return {"status": "Authentication successful. Credentials saved."}
