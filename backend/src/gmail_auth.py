from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from pathlib import Path

def get_file_path(filename: str) -> Path | None:
    for path in Path(__file__).resolve().parents:
        if path.name != "backend": continue
        return path / filename
    return None


# The permissions we need (Read only)
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_FILE_NAME = "auth_token.json"
AUTH_CREDENTIALS_FILE = get_file_path("auth_credentials.json")


def authenticate_gmail():
    creds = None
    # 1. Check if we already have a token
    
    token_path = get_file_path(TOKEN_FILE_NAME)
    
    if token_path and token_path.exists():
        creds = Credentials.from_authorized_user_file(f'{TOKEN_FILE_NAME}', SCOPES)

    # 2. If no valid token, let's log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # This opens the browser
            flow = InstalledAppFlow.from_client_secrets_file(
                str(AUTH_CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 3. Save the token for next time
        with open(str(token_path), 'w') as token:
            token.write(creds.to_json())
            print(f"Success! {TOKEN_FILE_NAME} created.")

    return creds

if __name__ == '__main__':
    authenticate_gmail()