from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import sys
import json
import base64
import email
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
import mimetypes
import os

from pprint import pprint

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.settings.basic',
    'https://www.googleapis.com/auth/gmail.metadata'
]


def SendMessage(service, userId, encoded_message):
    message = (service.users().messages().send(userId=userId, body=encoded_message).execute())
    return message


def CreateMessage(service, userId, threadId, fromEmail, subjectEmail, sendAlias):
    message_text = '<div><span style="font-family:Roboto,&quot;Helvetica Neue&quot;,Helvetica,Arial,sans-serif;font-size:12.8px">The response was:</span><br style="font-family:Roboto,&quot;Helvetica Neue&quot;,Helvetica,Arial,sans-serif;font-size:12.8px"><p style="font-family:monospace;font-size:12.8px">The email account that you tried to reach does not exist. Please try double-checking the recipient\'s email address for typos or unnecessary spaces. Learn more at&nbsp;<a href="https://support.google.com/mail/?p=NoSuchUser" style="font-family:Roboto,&quot;Helvetica Neue&quot;,Helvetica,Arial,sans-serif" target="_blank" data-saferedirecturl="https://www.google.com/url?q=https://support.google.com/mail/?p%3DNoSuchUser&amp;source=gmail&amp;ust=1550058176781000&amp;usg=AFQjCNFyvVFoIWc422emQFheOcPIjEAKhw">https://support.google.com/<wbr>mail/?p=NoSuchUser</a>&nbsp;<wbr>x22sor4004529oto.92 - gsmtp</p></div>'

    sendAsEmail = sendAlias.get('sendAsEmail', [])
    displayName = sendAlias.get('displayName', [])

    message = MIMEText(message_text, 'html')
    message['to'] = fromEmail
    message['from'] = displayName + '<' + sendAsEmail + '>'
    message['subject'] = subjectEmail
    encoded_message = {'threadId': threadId, 'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

    SendMessage(service, userId, encoded_message)


def ListSendAs(service, userId, threadId, fromEmail, subjectEmail):
    response = service.users().settings().sendAs().list(userId=userId).execute()

    aliases = []
    if 'sendAs' in response:
        aliases.extend(response['sendAs'])

        for sendAlias in aliases:
            sendAsEmail = sendAlias.get('sendAsEmail', [])

            if sendAsEmail == 'mailer-daemon@allanbendy.com':
                CreateMessage(service, userId, threadId, fromEmail, subjectEmail, sendAlias)


def GetMessage(service, userId, threadId, msgId):
    message = service.users().messages().get(userId=userId, id=msgId).execute()
    print('Message snippet: %s' % message['snippet'])

    headers = service.users().threads().get(userId=userId, id=threadId, format='metadata').execute()['messages'][0]['payload']['headers']

    for header in headers:
        if header['name'] == 'From':
            fromEmail = header['value']

        if header['name'] == 'Subject':
            subjectEmail = header['value']

    ListSendAs(service, userId, threadId, fromEmail, subjectEmail)


def ListMessagesMatchingQuery(service, userId, q=''):
    response = service.users().messages().list(userId=userId, q=q).execute()

    messages = []
    if 'messages' in response:
        messages.extend(response['messages'])

        for message in messages:
            msgId = message.get('id', [])
            threadId = message.get('threadId', [])

            print('threadId: ' + threadId)
            print('msgId: ' + msgId)

            GetMessage(service, userId, threadId, msgId)
    

def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
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
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    userId='me'
    q='from:allan.bendy@yahoo.com is:unread'

    ListMessagesMatchingQuery(service, userId, q)
   

if __name__ == '__main__':
    main()
