
import os
import json
import asyncio
import httpx
import logging
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from subscriptions import fetch_subscriptions, save_subscriptions, SUBSCRIPTIONS_FILE
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

# To run the app on the port specified in .env, use:
#   uvicorn main:app --reload --port $(grep FASTAPI_PORT .env | cut -d '=' -f2)


load_dotenv()

# Setup logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 300))  # seconds, default 5 min
CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI")
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

logger.debug(f"CLIENT_ID: {CLIENT_ID}")

app = FastAPI(
    title="YouTube Subscriptions Monitor",
    version="1.0.2"
)

@app.on_event("startup")
async def start_monitor():
    logger.info("Starting subscription monitor task...")
    asyncio.create_task(monitor_subscriptions())

async def monitor_subscriptions():
    prev_subs = None
    prev_subs_dict = {}
    prev_count = None
    if os.path.exists(SUBSCRIPTIONS_FILE):
        try:
            with open(SUBSCRIPTIONS_FILE) as f:
                prev_subs = json.load(f)
                prev_subs_dict = {s["channelId"]: s for s in prev_subs}
                prev_count = len(prev_subs)
        except json.JSONDecodeError:
            logger.warning(f"{SUBSCRIPTIONS_FILE} is empty or invalid. Starting with no previous subscriptions.")
            prev_subs = None
            prev_subs_dict = {}
            prev_count = None
    logger.info("Monitor loop started. Poll interval: %s seconds", POLL_INTERVAL)
    while True:
        try:
            logger.debug("Fetching current subscriptions...")
            current_subs = fetch_subscriptions()
            current_subs_dict = {s["channelId"]: s for s in current_subs}
            current_count = len(current_subs)
            logger.info(f"Fetched {current_count} subscriptions from API. Previous saved count: {prev_count if prev_count is not None else 'N/A'}.")
            logger.debug(f"First 5 channel IDs from API: {[s['channelId'] for s in current_subs[:5]]}")
            if prev_subs is not None:
                logger.debug(f"First 5 channel IDs from saved file: {[s['channelId'] for s in prev_subs[:5]]}")
                # Log sorted lists for debug
                sorted_prev_ids = sorted(prev_subs_dict.keys())
                sorted_curr_ids = sorted(current_subs_dict.keys())
                logger.debug(f"Sorted channel IDs from saved file: {sorted_prev_ids[:10]}")
                logger.debug(f"Sorted channel IDs from API: {sorted_curr_ids[:10]}")
                prev_ids = set(prev_subs_dict.keys())
                curr_ids = set(current_subs_dict.keys())
                if prev_ids != curr_ids:
                    added_ids = curr_ids - prev_ids
                    removed_ids = prev_ids - curr_ids
                    added = [current_subs_dict[cid] for cid in added_ids]
                    removed = [prev_subs_dict[cid] for cid in removed_ids]
                    logger.info(f"Subscriptions changed. Added: {len(added)}, Removed: {len(removed)}")
                    await notify_webhook(added, removed)
                else:
                    logger.debug("No subscription changes detected (sets of IDs identical).")
            else:
                logger.debug("No previous subscriptions found. Saving current list.")
            save_subscriptions(current_subs)
            prev_subs = current_subs
            prev_subs_dict = current_subs_dict
            prev_count = current_count
        except Exception as e:
            logger.error(f"Error monitoring subscriptions: {e}", exc_info=True)
        await asyncio.sleep(POLL_INTERVAL)

async def notify_webhook(added, removed):
    if not WEBHOOK_URL:
        logger.warning("No webhook URL set. Skipping notification.")
        return
    content = ""
    if added:
        content += f"Added: {[s['title'] for s in added]}\n"
    if removed:
        content += f"Removed: {[s['title'] for s in removed]}\n"
    data = {"content": content.strip()}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(WEBHOOK_URL, json=data)
        logger.info(f"Webhook notified. Status: {resp.status_code}. Content: {data['content']}")
    except Exception as e:
        logger.error(f"Failed to notify webhook: {e}", exc_info=True)

@app.get("/")
def root():
    logger.debug("Root endpoint accessed.")
    return {"status": "YouTube Subscriptions Monitor is running"}


# Endpoint to view subscriptions and count
@app.get("/subscriptions")
def get_subscriptions():
    logger.debug("/subscriptions endpoint accessed.")
    try:
        with open(SUBSCRIPTIONS_FILE) as f:
            subs = json.load(f)
        logger.info(f"Returning {len(subs)} subscriptions.")
        return {
            "count": len(subs),
            "subscriptions": subs
        }
    except Exception as e:
        logger.error(f"Error reading subscriptions: {e}", exc_info=True)
        return {"error": str(e)}
    
# Endpoint to send a test message to the webhook
@app.post("/test-webhook")
async def test_webhook():
    logger.debug("/test-webhook endpoint accessed.")
    if not WEBHOOK_URL:
        logger.warning("No webhook URL set for test.")
        return {"error": "No webhook URL set."}
    data = {"content": "This is a test notification from the YouTube Subscriptions Monitor."}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(WEBHOOK_URL, json=data)
        logger.info(f"Test webhook message sent. Status: {resp.status_code}")
        return {"status": "Test message sent.", "webhook_response_status": resp.status_code}
    except Exception as e:
        logger.error(f"Error sending test webhook: {e}", exc_info=True)
        return {"error": str(e)}

# --- OAuth2 Endpoints ---
@app.get("/authorize")
def authorize():
    logger.debug("/authorize endpoint accessed.")
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
    logger.info(f"Redirecting to Google OAuth2 authorization URL.")
    return RedirectResponse(auth_url)

@app.get("/oauth2callback")
def oauth2callback(request: Request):
    logger.debug("/oauth2callback endpoint accessed.")
    code = request.query_params.get("code")
    if not code:
        logger.error("No code provided in OAuth2 callback.")
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
    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        # Save credentials for later use
        with open("token.json", "w") as token:
            token.write(creds.to_json())
        logger.info("OAuth2 authentication successful. Credentials saved.")
        return {"status": "Authentication successful. Credentials saved."}
    except Exception as e:
        logger.error(f"OAuth2 callback error: {e}", exc_info=True)
        return {"error": str(e)}
