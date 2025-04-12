# backend/messaging/services/sms_service.py
from twilio.rest import Client

def send_sms(to_number: str, message: str) -> bool:
    client = Client(account_sid, auth_token)
    try:
        client.messages.create(to=to_number, from_=from_number, body=message)
        return True
    except Exception as e:
        # log exception
        return False