

import logging
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# Setup logging
import os
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

SUBSCRIPTIONS_FILE = "subscriptions.json"

# Load credentials from token.json
def get_credentials():
    if not os.path.exists("token.json"):
        logger.error("OAuth token not found. Please authenticate first.")
        raise Exception("OAuth token not found. Please authenticate first.")
    logger.debug("Loading credentials from token.json")
    return Credentials.from_authorized_user_file("token.json")

# Fetch all subscriptions for the authenticated user
def fetch_subscriptions():
    logger.debug("Fetching subscriptions from YouTube API...")
    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)
    subs = []
    next_page_token = None
    total_results = None
    try:
        while True:
            request = youtube.subscriptions().list(
                part="snippet",
                mine=True,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
            if total_results is None:
                total_results = response.get("pageInfo", {}).get("totalResults")
            for item in response.get("items", []):
                subs.append({
                    "channelId": item["snippet"]["resourceId"]["channelId"],
                    "title": item["snippet"]["title"]
                })
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
        logger.info(f"Fetched {len(subs)} subscriptions.")
        return subs
    except Exception as e:
        logger.error(f"Error fetching subscriptions: {e}", exc_info=True)
        raise

# Save subscriptions to a JSON file
def save_subscriptions(subs):
    logger.debug("Saving subscriptions to file...")
    subs_sorted = sorted(subs, key=lambda x: x["title"].lower())
    try:
        with open(SUBSCRIPTIONS_FILE, "w") as f:
            json.dump(subs_sorted, f, indent=2)
        logger.info(f"Saved {len(subs_sorted)} subscriptions to {SUBSCRIPTIONS_FILE}.")
    except Exception as e:
        logger.error(f"Error saving subscriptions: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("Running as main module. Fetching and saving subscriptions...")
    try:
        subs = fetch_subscriptions()
        save_subscriptions(subs)
        logger.info(f"Fetched and saved {len(subs)} subscriptions.")
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
