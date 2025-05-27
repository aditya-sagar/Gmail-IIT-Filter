import warnings
warnings.filterwarnings('ignore', category=Warning)

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os

# Scopes for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# List of email accounts to authenticate
EMAIL_ACCOUNTS = [
    'aditya.sagar.official@gmail.com',
    'aditya.sagar.iitd@gmail.com',
    'aditya.ninetythree@gmail.com'
]

def authenticate_account(account):
    token_file = f'token_{account.split("@")[0]}.pickle'
    creds = None
    # Check if token already exists
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print(f"Please authenticate for {account}...")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    print(f"Authentication successful for {account}. Token saved to {token_file}.")

def main():
    for account in EMAIL_ACCOUNTS:
        authenticate_account(account)

if __name__ == '__main__':
    main()