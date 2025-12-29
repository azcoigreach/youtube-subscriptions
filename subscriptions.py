import os
import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv()

SUBSCRIPTIONS_FILE = "subscriptions.json"

# Load credentials from token.json
def get_credentials():
    if not os.path.exists("token.json"):
        raise Exception("OAuth token not found. Please authenticate first.")
    return Credentials.from_authorized_user_file("token.json")

# Fetch all subscriptions for the authenticated user
def fetch_subscriptions():
    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)
    subs = []
    next_page_token = None
    while True:
        request = youtube.subscriptions().list(
            part="snippet",
            mine=True,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()
        for item in response.get("items", []):
            subs.append({
                "channelId": item["snippet"]["resourceId"]["channelId"],
                "title": item["snippet"]["title"]
            })
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
    return subs

# Save subscriptions to a JSON file
def save_subscriptions(subs):
    with open(SUBSCRIPTIONS_FILE, "w") as f:
        json.dump(subs, f, indent=2)

if __name__ == "__main__":
    subs = fetch_subscriptions()
    save_subscriptions(subs)
    print(f"Fetched and saved {len(subs)} subscriptions.")
