# api/accounts/utils.py
from messaging.services.sms_service import send_sms
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def send_verification_sms(user):
    """
    Send verification SMS with improved error handling
    """
    try:
        token = user.generate_verification_token()
        verification_link = f"{settings.SITE_URL}/verify_phone/{token}"

        message = f"Hi {user.first_name}, verify your account here: {verification_link}"

        if not user.phone_number:
            logger.warning(f"No phone number found for user {user.username}. Cannot send SMS.")
            return False

        send_sms(user.phone_number, message)
        logger.info(f"Verification SMS sent to {user.phone_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification SMS to {user.phone_number}: {str(e)}")
        return False


def send_reset_sms(user, reset_token):
    """
    Send password reset SMS with unique token
    """
    try:
        reset_link = f"{settings.SITE_URL}/reset-password/{reset_token}"
        message = f"Reset your password here: {reset_link} (expires in 1 hour)"

        # Store token and timestamp
        user.password_reset_token = reset_token
        user.password_reset_token_created_at = timezone.now()
        user.save()

        if not user.phone_number:
            logger.warning(f"No phone number found for user {user.username}. Cannot send SMS.")
            return False

        send_sms(user.phone_number, message)
        logger.info(f"Password reset SMS sent to {user.phone_number}")
        return True
    except Exception as e:
        logger.error(f"Error sending reset SMS to {user.phone_number}: {e}")
        return False
