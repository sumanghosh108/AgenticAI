"""
Google OAuth 2.0 helper for Streamlit.

Flow:
  1. User clicks "Continue with Google"
  2. Generates Google OAuth URL → user redirected to Google consent screen
  3. Google redirects back to Streamlit with ?code=xxx
  4. Exchange code for token → fetch user profile (email, name)
  5. Auto-create or login the user in our database
"""

import os
from pathlib import Path
from requests_oauthlib import OAuth2Session
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(str(_env_path), override=True)

# Google endpoints
AUTH_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def _get_client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "")


def _get_client_secret() -> str:
    return os.getenv("GOOGLE_CLIENT_SECRET", "")


def _get_redirect_uri() -> str:
    return os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")


def is_google_oauth_configured() -> bool:
    """Check if Google OAuth credentials are set."""
    cid = _get_client_id()
    secret = _get_client_secret()
    return bool(cid and secret)


def get_google_auth_url() -> str:
    """Generate the Google OAuth consent URL."""
    oauth = OAuth2Session(
        _get_client_id(),
        redirect_uri=_get_redirect_uri(),
        scope=SCOPES,
    )
    auth_url, _ = oauth.authorization_url(
        AUTH_BASE_URL,
        access_type="offline",
        prompt="select_account",
    )
    return auth_url


def exchange_code_for_user(code: str) -> dict:
    """
    Exchange the authorization code for an access token,
    then fetch the user's Google profile.

    Returns:
        dict with keys: email, name, picture, google_id
    """
    # Allow http for localhost (development only)
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    oauth = OAuth2Session(
        _get_client_id(),
        redirect_uri=_get_redirect_uri(),
        scope=SCOPES,
    )

    token = oauth.fetch_token(
        TOKEN_URL,
        code=code,
        client_secret=_get_client_secret(),
    )

    # Fetch user info
    resp = oauth.get(USERINFO_URL)
    user_info = resp.json()

    return {
        "email": user_info.get("email", ""),
        "name": user_info.get("name", ""),
        "picture": user_info.get("picture", ""),
        "google_id": user_info.get("id", ""),
    }
