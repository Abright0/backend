# backend/messaging/services/sms_service.py
from twilio.rest import Client
from django.conf import settings


def send_sms(to_number, message):
    if getattr(settings, 'USE_DUMMY_SMS', True):
        print(f"[DUMMY SMS] To: {to_number}")
        print(f"[DUMMY SMS] To: {message}")
        return

    print('send_sms')
    print(to_number)
    print(message)
    print(settings.TWILIO_ACCOUNT_SID + ' ' + settings.TWILIO_AUTH_TOKEN)
    print( settings.TWILIO_ACCOUNT_SID + ' ' + settings.TWILIO_AUTH_TOKEN)
    if not to_number or not message:
        return

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    client.messages.create(
        to=to_number,
        from_=settings.TWILIO_PHONE_NUMBER,
        body=message
    )