# api/accounts/utils.py
from messaging.services.sms_service import send_sms
from django.conf import settings
from django.utils import timezone
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)

def send_verification_sms(user):
    try:
        if not user.phone_number:
            logger.warning(f"No phone number found for user {user.username}. Cannot send verification.")
            return False

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        verification = client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verifications.create(
            to=user.phone_number,
            channel="sms"
        )

        logger.info(f"Twilio verification initiated for {user.phone_number}. Status: {verification.status}")
        return True
    except Exception as e:
        logger.error(f"Failed to start Twilio verification for {user.phone_number}: {str(e)}")
        return False

def check_verification_code(user, code):
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        verification_check = client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verification_checks.create(
            to=user.phone_number,
            code=code
        )

        return verification_check.status == "approved"
    except Exception as e:
        logger.error(f"Verification code check failed for {user.phone_number}: {e}")
        return False


def send_reset_sms(user):
    """
    Send password reset verification code via Twilio Verify
    """
    try:
        if not user.phone_number:
            logger.warning(f"No phone number found for user {user.username}. Cannot send SMS.")
            return False

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        verification = client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verifications.create(
            to=user.phone_number,
            channel="sms"
        )

        logger.info(f"Password reset verification code sent to {user.phone_number}. Status: {verification.status}")
        return True
    except Exception as e:
        logger.error(f"Error sending Twilio verification code to {user.phone_number}: {e}")
        return False



def check_reset_code(user, code):
    """
    Check if the user-provided password reset code is valid
    """
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        verification_check = client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verification_checks.create(
            to=user.phone_number,
            code=code
        )

        return verification_check.status == "approved"
    except Exception as e:
        logger.error(f"Error verifying reset code for {user.phone_number}: {e}")
        return False
