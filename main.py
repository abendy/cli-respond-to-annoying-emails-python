import pickle
import os
import sys
import json
import base64
import email
import mimetypes
import re
import click
import codecs
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.base import MIMEBase
from email.mime.text import MIMEText

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.metadata',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.settings.basic'
]

def validate_email(ctx, param, value):
    match = re.match(r'^[^@]*\@[\w\.]+\w+$', value)
    if match is not None:
        return value
    else:
        raise click.BadParameter('Email format: user@domain.com OR @domain.com')

@click.command()
@click.option("-e", "--email", help="Email search string", required=True, callback=validate_email)
@click.option("-k", "--keyword", help="Search keyword")
@click.option("-t", "--template", help="Email Reply HTML Template", required=True)
def main(email, keyword, template):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('config/token.pickle'):
        with open('config/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_id.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('config/token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    q='is:unread from:' + email

    if keyword is not None:
        q += " " + keyword

    print('Email search: `%s`' % q)

    response = service.users().messages().list(userId='me', q=q).execute() #pylint: disable=no-member

    messages = []
    if 'messages' in response:
        messages.extend(response['messages'])

    for message in messages:
        msg_id = message.get('id', [])
        thread_id = message.get('threadId', [])

        # Get message
        message = service.users().messages().get(userId='me', id=msg_id).execute() #pylint: disable=no-member

        # Get headers
        headers = service.users().threads().get(userId='me', id=thread_id, format='metadata').execute()['messages'][0]['payload']['headers'] #pylint: disable=no-member

        print('Message snippet: %s' % message['snippet'])
        print('thread_id: %s' % thread_id)
        print('msg_id: %s' % msg_id)

        for header in headers:
            if header['name'] == 'From':
                from_email = header['value']

            if header['name'] == 'Subject':
                subject_email = header['value']

        file = template + ".html"
        f=codecs.open('templates/' + file, 'r')
        message_text = f.read()

        message = MIMEText(message_text, 'html')
        message['to'] = from_email
        message['from'] = 'Mailer Delivery Subsystem <mailer-daemon@mailserv.allanbendy.com>'
        message['reply-to'] = 'no-reply@allanbendy.com'
        message['subject'] = subject_email
        body = {'threadId': thread_id, 'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

        # Mark as read
        service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute() #pylint: disable=no-member

        # Send reply
        message = (service.users().messages().send(userId='me', body=body).execute()) #pylint: disable=no-member

        print('Reply sent')

if __name__ == '__main__':
    main() #pylint: disable=no-value-for-parameter
