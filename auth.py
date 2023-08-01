import os
import json
import pickle
from google.auth import default
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

def create_flow(scopes):
    # Load the client secrets file
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secret.json',
        scopes=scopes
    )
    
    return flow

def get_credentials():
    """Gets the credentials for the Google Calendar API."""

    # Path to your client secrets file
    client_secrets_file = 'client_secret.json'

    # List of scopes your application is requesting access to
    scopes = ['https://www.googleapis.com/auth/calendar.readonly']

    creds = None

    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def authenticate(token_file='my_token.json'):
    creds = None

    # Check if there are existing credentials
    if os.path.exists(token_file):
        with open(token_file, 'r') as token:
            creds = Credentials.from_authorized_user_info(json.load(token))

    # If there are no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = get_credentials()

    with open(token_file, 'w') as token:
        token.write(creds.to_json())

    return creds

if __name__ == '__main__':
    creds = authenticate()
    print(creds)
