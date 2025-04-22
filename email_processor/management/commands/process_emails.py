import base64
import requests
from django.core.management.base import BaseCommand
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings

class Command(BaseCommand):
    help = "Fetches emails from a specific sender and sends them to the API."

    def handle(self, *args, **options):
        SERVICE_ACCOUNT_FILE = settings.GMAIL_SERVICE_ACCOUNT_FILE
        USER_EMAIL = settings.GMAIL_USER_EMAIL
        API_ENDPOINT = settings.API_ENDPOINT
        SPECIFIC_SENDER = settings.SPECIFIC_SENDER
        SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

        if not all([SERVICE_ACCOUNT_FILE, USER_EMAIL, API_ENDPOINT, SPECIFIC_SENDER]):
            self.stdout.write(self.style.ERROR(
                "Missing one or more required settings: GMAIL_SERVICE_ACCOUNT_FILE, GMAIL_USER_EMAIL, API_ENDPOINT, SPECIFIC_SENDER"
            ))
            return

        def get_plain_text_body(payload):
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                        try:
                            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        except Exception as decode_error:
                            self.stdout.write(self.style.WARNING(f"    Warning: Could not decode part - {decode_error}"))
                    elif 'parts' in part:
                        nested = get_plain_text_body(part)
                        if nested:
                            return nested
            elif payload.get('mimeType') == 'text/plain' and 'data' in payload.get('body', {}):
                try:
                    return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
                except Exception as decode_error:
                    self.stdout.write(self.style.WARNING(f"    Warning: Could not decode main body - {decode_error}"))
            return ""

        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            delegated = credentials.with_subject(USER_EMAIL)
            gmail = build('gmail', 'v1', credentials=delegated)

            self.stdout.write(self.style.MIGRATE_HEADING(f"Checking emails for {USER_EMAIL} from {SPECIFIC_SENDER}..."))

            page_token = None
            processed_count = 0

            while True:
                results = gmail.users().messages().list(
                    userId=USER_EMAIL,
                    q=f'from:{SPECIFIC_SENDER}',
                    maxResults=50,
                    pageToken=page_token
                ).execute()

                messages = results.get('messages', [])
                if not messages:
                    if page_token is None:
                        self.stdout.write(self.style.SUCCESS("No new emails found from the specified sender."))
                    break

                self.stdout.write(self.style.NOTICE(f"Found {len(messages)} emails from {SPECIFIC_SENDER} on this page..."))

                for msg in messages:
                    message_id = msg['id']
                    try:
                        email = gmail.users().messages().get(
                            userId=USER_EMAIL, id=message_id, format='full').execute()

                        headers = email.get('payload', {}).get('headers', [])
                        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                        from_addr = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'No Sender')
                        body = get_plain_text_body(email.get('payload', {}))

                        self.stdout.write("-" * 50)
                        self.stdout.write(f"Processing Message ID: {message_id}")
                        self.stdout.write(f"From: {from_addr}")
                        self.stdout.write(f"Subject: {subject}")
                        self.stdout.write(f"Body Snippet: {email.get('snippet', '')}")
                        self.stdout.write("-" * 50)

                        email_data = {
                            'sender': from_addr,
                            'subject': subject,
                            'body': body,
                            'message_id': message_id,
                        }

                        try:
                            response = requests.post(API_ENDPOINT, json=email_data)
                            response.raise_for_status()
                            self.stdout.write(self.style.SUCCESS(f"Successfully sent data for message {message_id} to API."))
                        except requests.exceptions.RequestException as e:
                            self.stdout.write(self.style.ERROR(f"Error sending data for message {message_id}: {e}"))
                            continue

                        gmail.users().messages().modify(
                            userId=USER_EMAIL,
                            id=message_id,
                            body={'removeLabelIds': ['UNREAD']}
                        ).execute()
                        self.stdout.write(self.style.SUCCESS(f"Marked message {message_id} as read."))
                        processed_count += 1

                    except HttpError as http_error:
                        self.stdout.write(self.style.ERROR(f"Error processing message {message_id}: {http_error}"))
                    except Exception as msg_error:
                        self.stdout.write(self.style.ERROR(f"Unexpected error processing message {message_id}: {msg_error}"))

                page_token = results.get('nextPageToken')
                if not page_token:
                    break

            self.stdout.write(self.style.MIGRATE_HEADING(f"\nFinished processing. Processed {processed_count} emails."))

        except HttpError as error:
            self.stdout.write(self.style.ERROR(f"An API error occurred: {error}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unexpected top-level error: {str(e)}"))
