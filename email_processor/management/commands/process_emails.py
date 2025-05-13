import base64
import re
import requests  # still imported, in case you re-enable later
from django.core.management.base import BaseCommand
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings


class Command(BaseCommand):
    help = "Fetches emails from a specific sender and prints their data with optional invoice extraction."

    def handle(self, *args, **options):
        if not settings.GMAIL_CREDENTIALS:
            self.stdout.write(self.style.ERROR("Missing Gmail credentials."))
            return

        if not all([settings.GMAIL_USER_EMAIL, settings.SPECIFIC_DOMAIN]):
            self.stdout.write(self.style.ERROR("Missing one or more Gmail config values."))
            return

        delegated = settings.GMAIL_CREDENTIALS.with_subject(settings.GMAIL_USER_EMAIL)
        gmail = build('gmail', 'v1', credentials=delegated)

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

        def extract_invoice_info(body):
            invoice_data = {}
            invoice_no_match = re.search(r'Invoice\s+#?:?\s*(\d+)', body, re.IGNORECASE)
            if invoice_no_match:
                invoice_data['invoice_number'] = invoice_no_match.group(1)

            amount_match = re.search(r'Total\s+Amount:?\s*\$?([\d,]+\.\d{2})', body, re.IGNORECASE)
            if amount_match:
                invoice_data['amount'] = amount_match.group(1)

            date_match = re.search(r'Due\s+Date:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', body)
            if date_match:
                invoice_data['due_date'] = date_match.group(1)

            return invoice_data

        try:
            self.stdout.write(self.style.MIGRATE_HEADING(f"Checking emails for {settings.GMAIL_USER_EMAIL} from {settings.SPECIFIC_DOMAIN}..."))

            page_token = None
            processed_count = 0

            while True:
                results = gmail.users().messages().list(
                    userId=settings.GMAIL_USER_EMAIL,
                    q=f'from:{settings.SPECIFIC_DOMAIN} is:unread',
                    maxResults=50,
                    pageToken=page_token
                ).execute()

                messages = results.get('messages', [])
                if not messages:
                    if page_token is None:
                        self.stdout.write(self.style.SUCCESS("No new emails found from the specified sender."))
                    break

                self.stdout.write(self.style.NOTICE(f"Found {len(messages)} emails from {settings.SPECIFIC_DOMAIN} on this page..."))

                for msg in messages:
                    message_id = msg['id']
                    try:
                        email = gmail.users().messages().get(
                            userId=settings.GMAIL_USER_EMAIL, id=message_id, format='full').execute()

                        headers = email.get('payload', {}).get('headers', [])
                        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                        from_addr = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'No Sender')
                        body = get_plain_text_body(email.get('payload', {}))
                        invoice_fields = extract_invoice_info(body)

                        email_data = {
                            'sender': from_addr,
                            'subject': subject,
                            'body': body,
                            'message_id': message_id,
                            **invoice_fields,
                        }

                        self.stdout.write("-" * 60)
                        self.stdout.write(f"Email Data for Message ID: {message_id}")
                        for key, value in email_data.items():
                            self.stdout.write(f"{key}: {value}")
                        self.stdout.write("-" * 60)

                        # Commented out: API submission
                        # response = requests.post(settings.API_ENDPOINT, json=email_data)
                        # response.raise_for_status()
                        # self.stdout.write(self.style.SUCCESS(f"Successfully sent data for message {message_id} to API."))

                        # Optionally: skip marking as read
                        # gmail.users().messages().modify(
                        #     userId=settings.GMAIL_USER_EMAIL,
                        #     id=message_id,
                        #     body={'removeLabelIds': ['UNREAD']}
                        # ).execute()

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
