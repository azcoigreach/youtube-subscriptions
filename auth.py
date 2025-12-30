
import logging
from dotenv import load_dotenv

load_dotenv()

# Setup logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI()

CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI")
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

@app.get("/")
def root():
    logger.debug("Root endpoint accessed.")
    return {"status": "YouTube Subscriptions Monitor is running"}

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
    logger.info("Redirecting to Google OAuth2 authorization URL.")
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
