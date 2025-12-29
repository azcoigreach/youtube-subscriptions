

# YouTube Subscriptions Monitor ![version](https://img.shields.io/badge/version-1.0.2-blue)


**Current Version:** 1.0.2

Monitor your YouTube subscriptions for changes and receive webhook notifications when channels are added or removed.

## Features
- Monitors your YouTube account for subscription changes
- Sends push notifications to a webhook (e.g., Discord) when channels are added or removed
- User-readable subscription list (JSON)
- FastAPI endpoints for health, viewing subscriptions, and testing webhook
- OAuth2 authentication with Google
- Configurable polling interval and port via `.env`

## Setup
1. **Clone the repository:**
	```bash
	git clone https://github.com/azcoigreach/youtube-subscriptions.git
	cd youtube-subscriptions
	```

2. **Install dependencies:**
	```bash
	pip install -r requirements.txt
	# or with poetry
	poetry install
	```

3. **Create and configure your `.env` file:**
	- Copy `.env.example` to `.env` and fill in your credentials:
	  ```env
	  YOUTUBE_CLIENT_ID=your-google-client-id
	  YOUTUBE_CLIENT_SECRET=your-google-client-secret
	  YOUTUBE_REDIRECT_URI=http://localhost:8088/oauth2callback
	  WEBHOOK_URL=your-webhook-url
	  POLL_INTERVAL=300
	  FASTAPI_PORT=8088
	  ```
	- Make sure the redirect URI matches one of the authorized URIs in your Google Cloud Console.

4. **Run the app:**
	```bash
	uvicorn main:app --reload --port $(grep FASTAPI_PORT .env | cut -d '=' -f2)
	```

5. **Authenticate with Google:**
	- Visit `http://localhost:8088/authorize` (replace port if changed) and complete the OAuth2 flow.

## API Endpoints

- `GET /` — Health check/status
- `GET /subscriptions` — View current subscriptions and count
- `POST /test-webhook` — Send a test notification to your webhook
- `GET /authorize` — Start OAuth2 authentication
- `GET /oauth2callback` — OAuth2 callback (used by Google)

## How it works
- The app polls your YouTube subscriptions at the interval set in `.env` (`POLL_INTERVAL` in seconds).
- If any channels are added or removed, a notification is sent to your webhook.
- The current subscription list is saved in `subscriptions.json`.

## Webhook Example
The webhook receives a message like:
```
Added: ['New Channel']
Removed: ['Old Channel']
```

## Notes
- You must use OAuth2 credentials from the Google Cloud Console with YouTube Data API v3 enabled.
- The app is intended for personal/local use and is not a public web service.
- To change the FastAPI port, edit `FASTAPI_PORT` in `.env` and restart the app.

---
MIT License
