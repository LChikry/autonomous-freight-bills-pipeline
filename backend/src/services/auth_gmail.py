from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from pathlib import Path

def get_credentials_filepath(filename: str) -> Path | None:
    for path in Path(__file__).resolve().parents:
        if path.name != "backend": continue
        return path / "credentials" / filename
    return None

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
GMAIL_OAUTH_TOKEN = get_credentials_filepath("gmail_oauth_token.json")
GMAIL_OAUTH_CLIENT = get_credentials_filepath("gmail_oauth_client.json")

def authenticate_gmail():
    creds = None
    if GMAIL_OAUTH_TOKEN and GMAIL_OAUTH_TOKEN.exists():
        creds = Credentials.from_authorized_user_file(GMAIL_OAUTH_TOKEN, SCOPES)

    # 2. If no valid token, let's log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # This opens the browser
            flow = InstalledAppFlow.from_client_secrets_file(
                str(GMAIL_OAUTH_CLIENT), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 3. Save the token for next time
        with open(str(GMAIL_OAUTH_TOKEN), 'w') as token:
            token.write(creds.to_json())
            print(f"Success! {GMAIL_OAUTH_TOKEN} created.")

    return creds

def get_gmail_service():
    creds = authenticate_gmail()
    return build('gmail', 'v1', credentials=creds)

if __name__ == '__main__':
    authenticate_gmail()