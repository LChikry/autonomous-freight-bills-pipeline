from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import logging

from config import config

logger = logging.getLogger(__name__)

def _authenticate_gmail():
    logger.info("Loading Gmail OAuth credentials")
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    creds = None
    if config.gmail_token_path.exists():
        creds = Credentials.from_authorized_user_file(config.gmail_token_path, SCOPES)
        if creds.valid: return creds
    
    if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(config.gmail_client_path), SCOPES)
        creds = flow.run_local_server(port=0)

    with open(config.gmail_token_path, 'w') as token:
        token.write(creds.to_json())

    logger.info(f"New Gmail credentials token was saved to {config.gmail_token_path}")

    return creds

def get_gmail_service():
    creds = _authenticate_gmail()
    logger.info("Authenticating Gmail account")
    return build('gmail', 'v1', credentials=creds)

if __name__ == '__main__':
    _authenticate_gmail()