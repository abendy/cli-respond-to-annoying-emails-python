from __future__ import print_function
import pickle
import os
import os.path
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
from apiclient import errors

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://mail.google.com/'
]

def send_response(message_service, load_message, body, template):
    # # Mark as read
    # message_id = load_message['id']
    # message_service.modify(
    #     userId='me',
    #     id=message_id,
    #     body={'removeLabelIds': ['UNREAD']}
    # ).execute()

    # Send reply
    try:
        sender = (message_service.messages().send(
            userId='me',
            body=body
        ).execute())
        print(sender)

    except errors.HttpError as error:
        print('An error occurred: %s' % error)

def build_response(message_service, load_message, template):
    headers = load_message['payload']['headers']
    for header in headers:
        if header['name'] == 'From':
            from_email = header['value']

        if header['name'] == 'Subject':
            subject_email = header['value']

        if header['name'] == 'Message-ID':
            header_message_id = header['value']

        if header['name'] == 'References':
            header_references = header['value']

        if header['name'] == 'In-Reply-To':
            header_in_reply_to = header['value']

    # Get template
    file = template + ".html"
    f=codecs.open('templates/' + file, 'r')
    message_text = f.read()
    print('template: %s' % template)

    # Create response
    reply = MIMEText(message_text, 'html')
    reply['to'] = from_email

    if template == "cc":
        reply['from'] = 'Allan Bendy <allan.bendy@gmail.com>'
        reply['reply-to'] = 'allan.bendy@gmail.com'

    elif template == "404":
        reply['from'] = 'Mailer Delivery Subsystem <mailer-daemon@mailserv.allanbendy.com>'
        reply['reply-to'] = 'no-reply@allanbendy.com'

    reply['subject'] = 'Re: ' + subject_email

    reply['Message-ID'] = header_message_id
    # reply['References'] = header_references
    # reply['In-Reply-To'] = header_in_reply_to
    reply['References'] = header_message_id
    reply['In-Reply-To'] = header_message_id

    body = {
        'threadId': load_message['threadId'],
        'raw': base64.urlsafe_b64encode(reply.as_bytes()).decode()
    }

    send_response(message_service, load_message, body, template)

def get_message(message_service, message, template):
    # Message and thread IDs
    message_id = message['id']
    print('message_id: %s' % message_id)

    # Get message headers
    metadata_headers = ['From', 'Subject', 'Message-ID', 'References', 'In-Reply-To']
    load_message = message_service.messages().get(
        userId='me',
        id=message_id,
        format='metadata',
        metadataHeaders=metadata_headers
    ).execute()
    print('Message snippet: %s' % load_message['snippet'])

    build_response(message_service, load_message, template)

def query(message_service, args):
    email = args[0]
    keyword = args[1]
    template = args[2]
    unread = args[3]

    # Build the search query
    q="from:" + email

    # Add `keyword` flag to search query
    if keyword is not None:
        q += " " + keyword

    # Add `unread` flag to search query
    if unread is True:
        q += " is:unread"

    # Print search query
    print('Email search: `%s`' % q)

    # Get the messages from the search query
    response = message_service.messages().list(
        userId='me',
        q=q
    ).execute().get('messages', [])

    # Loop over search query response
    for message in response:
        get_message(message_service, message, template)

def validate_email(ctx, param, value):
    match = re.match(r'^[^@]*\@[\w\.]+\w+$', value)
    if match is not None:
        return value
    else:
        raise click.BadParameter('Email format: user@domain.com OR @domain.com')

@click.command()
@click.option("-e", "--email", help="Email search string", required=True, callback=validate_email)
@click.option("-k", "--keyword", help="Search keyword")
@click.option("-u", "--unread", help="Unread emails only", is_flag=True, default=False)
@click.option("-t", "--template", help="Email reply template", required=True)
def auth(email, keyword, unread, template):
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
                'config/client_id.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('config/token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Init the API/service
    service = build('gmail', 'v1', credentials=creds)
    message_service = service.users() #pylint: disable=no-member

    args = [
        email,
        keyword,
        template,
        unread
    ]

    # Execute query
    query(message_service, args)

if __name__ == '__main__':
    auth() #pylint: disable=no-value-for-parameter
