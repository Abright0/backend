# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password
import uuid
import phonenumbers
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


class User(AbstractUser):
    # AbstractUser already includes:
    # - username
    # - first_name
    # - last_name
    # - email
    # - password
    # - is_active
    # - is_staff
    # - is_superuser
    # - date_joined
    
    username = models.CharField(
        max_length=32, 
        unique=True,
        default='defaultuser'
    )
    
    email = models.EmailField(
        unique=True,
        default='default@example.com'
    )

    # info
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        unique=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )

    # roles
    is_driver = models.BooleanField(default=False)
    is_customer_service = models.BooleanField(default=False)
    is_inside_manager = models.BooleanField(default=False)
    is_warehouse_manager = models.BooleanField(default=False)
    is_store_manager = models.BooleanField(default=False)

    # Verification
    is_phone_verified = models.BooleanField(default=False)
    phone_verification_token = models.CharField(max_length=82, null=True)
    password_reset_token = models.CharField(max_length=255, null=True, blank=True)
    password_reset_token_created_at = models.DateTimeField(null=True, blank=True)

    # stores
    stores = models.ManyToManyField('stores.Store', related_name='store_users')

    class Meta(AbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'

    def __str__(self):
        return self.username

    def generate_verification_token(self):
        """Generate a new verification token for user"""
        self.phone_verification_token = str(uuid.uuid4())
        self.save()
        print(f"Generated token for user {self.username}: {self.phone_verification_token}")
        return self.phone_verification_token

    def get_roles(self):
        if self.is_superuser:
            return ['superuser']
        
        roles = []
        if self.is_manager and self.is_customer_service and self.is_driver:
            roles.append('store_manager')
        elif self.is_manager and self.is_customer_service:
            roles.append('inside_manager')
        elif self.is_manager and self.is_driver:
            roles.append('warehouse_manager')
        elif self.is_customer_service:
            roles.append('customer_service')
        elif self.is_driver:
            roles.append('driver')
        return roles

    def clean(self):
        super().clean()
        if self.phone_number:
            try:
                parsed = phonenumbers.parse(self.phone_number, 'US')  # Replace 'US' with your default region
                if not phonenumbers.is_valid_number(parsed):
                    raise ValidationError({'phone_number': 'Invalid phone number.'})
                # Format to E.164
                self.phone_number = phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )
            except phonenumbers.NumberParseException:
                raise ValidationError({'phone_number': 'Could not parse phone number.'})