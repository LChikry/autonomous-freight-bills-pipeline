from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
from loguru import logger

from app.core import settings

def _authenticate_gmail():
    logger.debug("Authenticating Gmail account")
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    creds = None
    if settings.gmail_token_path.exists():
        logger.debug("Loading Gmail OAuth token")
        creds = Credentials.from_authorized_user_file(settings.gmail_token_path, SCOPES)
    
    # 1. Try to Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        logger.debug("Gmail credentials are expired")
        try:
            logger.debug("Attempting to refresh access token")
            creds.refresh(Request())
        except RefreshError:
            logger.debug("Refresh token is expired or revoked")
            creds = None

    # 2. If no valid creds (either because file didn't exist OR refresh failed above)
    if not creds or not creds.valid:
        logger.debug("Starting new authentication flow")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(settings.gmail_client_path), SCOPES)
        creds = flow.run_local_server(port=0)

        # Save the new credentials
        with open(settings.gmail_token_path, 'w') as token:
            token.write(creds.to_json())
        logger.debug(f"New Gmail credentials token was saved to {settings.gmail_token_path}")

    return creds

def get_gmail_service():
    creds = _authenticate_gmail()
    return build('gmail', 'v1', credentials=creds)

if __name__ == '__main__':
    _authenticate_gmail()