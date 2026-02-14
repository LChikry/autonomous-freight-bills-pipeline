from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
import logging

from core import settings

logger = logging.getLogger(__name__)

def _authenticate_gmail():
    logger.info("Loading Gmail OAuth credentials")
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    creds = None
    if settings.gmail_token_path.exists():
        creds = Credentials.from_authorized_user_file(settings.gmail_token_path, SCOPES)
    
    # 1. Try to Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            logger.info("Attempting to refresh access token...")
            creds.refresh(Request())
        except RefreshError:
            logger.warning("Refresh token is expired or revoked. Re-authenticating...")
            creds = None

    # 2. If no valid creds (either because file didn't exist OR refresh failed above)
    if not creds or not creds.valid:
        logger.info("Starting new authentication flow...")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(settings.gmail_client_path), SCOPES)
        creds = flow.run_local_server(port=0)

        # Save the new credentials
        with open(settings.gmail_token_path, 'w') as token:
            token.write(creds.to_json())
        logger.info(f"New Gmail credentials token was saved to {settings.gmail_token_path}")

    return creds

def get_gmail_service():
    creds = _authenticate_gmail()
    logger.info("Authenticating Gmail account")
    return build('gmail', 'v1', credentials=creds)

if __name__ == '__main__':
    _authenticate_gmail()