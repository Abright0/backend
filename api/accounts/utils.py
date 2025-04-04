from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string

import project.settings
import logging

logger = logging.getLogger(__name__)

def send_verification_email(user):
    """
    Send verification email with improved error handling
    """
    try:
        subject = 'Verify your email address'
        token = user.generate_verification_token()
        verification_link = f"{settings.SITE_URL}/verify_email/{token}"

        context = {
            'user': user,
            'verification_link': verification_link
        }
        
        html_message = render_to_string('accounts/email_verification.html', context)
        plain_message = render_to_string('accounts/email_verification.txt', context)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=True,  # Changed to True to prevent crashing
        )
        
        logger.info(f"Verification email sent to {user.email}")
        return True
    except Exception as e:
        # Log the error but don't crash
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        return False


def send_reset_email(user, reset_token):
    """
    Send password reset email with unique token
    """
    try:
        # Create reset link
        reset_link = f"{settings.SITE_URL}/reset-password/{reset_token}"
        
        # Store token and timestamp
        user.password_reset_token = reset_token
        user.password_reset_token_created_at = timezone.now()
        user.save()
        
        # Email context
        context = {
            'user': user,
            'reset_link': reset_link,
            'site_name': settings.SITE_NAME,
            'expiration_minutes': 60  # Token expires in 1 hour
        }
        
        # Render email templates
        subject = f'Password Reset for {settings.SITE_NAME}'
        html_message = render_to_string('accounts/password_reset_email.html', context)
        plain_message = render_to_string('accounts/password_reset_email.txt', context)
        
        # Send email
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=True,  # Changed to True to prevent crashing
        )
        
        logger.info(f"Password reset email sent to {user.email}")
        return True
    except Exception as e:
        # Log the error
        logger.error(f"Error sending reset email to {user.email}: {e}")
        return False