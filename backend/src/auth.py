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
AUTH_TOKEN_PATH = get_file_path("auth_token.json")
AUTH_CREDENTIALS_PATH = get_file_path("auth_credentials.json")


def authenticate_gmail():
    creds = None
    
    if AUTH_TOKEN_PATH and AUTH_TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(AUTH_TOKEN_PATH, SCOPES)

    # 2. If no valid token, let's log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # This opens the browser
            flow = InstalledAppFlow.from_client_secrets_file(
                str(AUTH_CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 3. Save the token for next time
        with open(str(AUTH_TOKEN_PATH), 'w') as token:
            token.write(creds.to_json())
            print(f"Success! {AUTH_TOKEN_PATH} created.")

    return creds

if __name__ == '__main__':
    authenticate_gmail()