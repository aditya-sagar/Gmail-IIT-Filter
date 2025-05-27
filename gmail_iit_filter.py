import warnings
warnings.filterwarnings('ignore', category=Warning)

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
import time
import httplib2
import google_auth_httplib2

# Scopes for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# List of email accounts to check
EMAIL_ACCOUNTS = [
    'aditya.sagar.official@gmail.com',
    'aditya.sagar.iitd@gmail.com',
    'aditya.ninetythree@gmail.com'
]

def authenticate_gmail(token_file='token.pickle'):
    creds = None
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception(f"No valid credentials found in {token_file}. Please run authenticate_accounts.py first.")
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    http = httplib2.Http(timeout=120)
    authorized_http = google_auth_httplib2.AuthorizedHttp(creds, http=http)
    return build('gmail', 'v1', http=authorized_http)

def search_emails(service, email_account):
    start_time = time.time()
    senders_to_cc_bcc = set()
    senders_trash_spam = set()
    api_calls = 0
    
    query = "iit"
    
    # Fetch emails with maxResults=500
    results = service.users().messages().list(userId='me', q=query, includeSpamTrash=True, maxResults=500, fields='messages(id,labelIds),nextPageToken').execute()
    messages = results.get('messages', [])
    api_calls += 1
    
    # Handle pagination
    while 'nextPageToken' in results:
        page_token = results['nextPageToken']
        try:
            results = service.users().messages().list(userId='me', q=query, includeSpamTrash=True, maxResults=500, pageToken=page_token, fields='messages(id,labelIds),nextPageToken').execute()
            messages.extend(results.get('messages', []))
            api_calls += 1
            # Rate limiting: delay every 100 API calls
            if api_calls % 100 == 0:
                time.sleep(0.5)
        except Exception as e:
            print(f"Error during pagination for {email_account}: {e}")
            break
    
    print(f"Number of messages for {email_account}: {len(messages)}")
    
    for i, message in enumerate(messages):
        retries = 3
        for attempt in range(retries):
            try:
                msg = service.users().messages().get(userId='me', id=message['id'], format='metadata', fields='payload/headers,labelIds').execute()
                api_calls += 1
                labels = msg.get('labelIds', [])
                is_trash_spam = 'TRASH' in labels or 'SPAM' in labels
                
                # Check if email was sent to the user
                recipient_match = False
                headers = msg.get('payload', {}).get('headers', [])
                for header in headers:
                    if header['name'].lower() in ['to', 'cc', 'bcc']:
                        value = header['value'].lower()
                        if email_account.lower() in value:
                            recipient_match = True
                            break
                
                if not recipient_match:
                    continue
                
                # Extract sender
                for header in headers:
                    if header['name'].lower() == 'from':
                        sender = header['value']
                        start = sender.find('<')
                        end = sender.find('>')
                        if start != -1 and end != -1:
                            email = sender[start + 1:end]
                        else:
                            email = sender.strip()
                        if '@' in email and '.' in email and 'iit' in email.lower():
                            email_lower = email.lower()
                            if is_trash_spam:
                                senders_trash_spam.add(email_lower)
                            else:
                                senders_to_cc_bcc.add(email_lower)
                        break
                break
            except Exception as e:
                if attempt < retries - 1:
                    print(f"Error on message {message['id']}, attempt {attempt + 1}/{retries}: {e}")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    print(f"Failed to process message {message['id']} after {retries} attempts: {e}")
                    break
        # Throttling: 0.2 seconds every 10 messages
        if (i + 1) % 10 == 0:
            time.sleep(0.2)
        # Rate limiting: delay every 100 API calls
        if api_calls % 100 == 0:
            time.sleep(0.5)

    end_time = time.time()
    duration = end_time - start_time
    print(f"Time to search emails for {email_account}: {int(duration // 60)} minutes {int(duration % 60)} seconds")
    
    return senders_to_cc_bcc, senders_trash_spam

def process_account(account, all_senders_to_cc_bcc, all_senders_trash_spam):
    start_time = time.time()
    print(f"\nProcessing {account}...")
    token_file = f'token_{account.split("@")[0]}.pickle'
    service = authenticate_gmail(token_file)
    senders_to_cc_bcc, senders_trash_spam = search_emails(service, account)
    all_senders_to_cc_bcc[account].update(senders_to_cc_bcc)
    all_senders_trash_spam[account].update(senders_trash_spam)
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"Time to process {account}: {int(duration // 60)} minutes {int(duration % 60)} seconds")

def main():
    total_start_time = time.time()
    
    all_senders_to_cc_bcc = {email: set() for email in EMAIL_ACCOUNTS}
    all_senders_trash_spam = {email: set() for email in EMAIL_ACCOUNTS}
    
    for account in EMAIL_ACCOUNTS:
        process_account(account, all_senders_to_cc_bcc, all_senders_trash_spam)
    
    for email in EMAIL_ACCOUNTS:
        print(f"\nSenders with 'iit' in email address for {email}:")
        print("From To/CC/BCC:")
        if all_senders_to_cc_bcc[email]:
            for sender in sorted(all_senders_to_cc_bcc[email]):
                print(sender)
        else:
            print("None found.")
        
        print("\nFrom Trash/Spam:")
        if all_senders_trash_spam[email]:
            for sender in sorted(all_senders_trash_spam[email]):
                print(sender)
        else:
            print("None found.")
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    print(f"\nTotal execution time: {int(total_duration // 60)} minutes {int(total_duration % 60)} seconds")

if __name__ == '__main__':
    main()