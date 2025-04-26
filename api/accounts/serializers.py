# api/accounts/serializers.py
from rest_framework import serializers
from accounts.models import User
from django.contrib.auth import get_user_model
from .utils import send_verification_sms
from stores.models import Store

import re

class UserSerializer(serializers.ModelSerializer):
    stores = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Store.objects.all()
    )

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'password',
            'first_name',
            'last_name',
            'phone_number',
            'is_driver',
            'is_customer_service',
            'is_manager',
            'is_active',
            'is_superuser',
            'date_joined',
            'stores',
            'is_phone_verified'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, data):
        request = self.context.get('request')
        requesting_user = request.user if request else None

        # Only require phone_number on CREATE (not update / partial update)
        if self.instance is None and not data.get('phone_number'):
            raise serializers.ValidationError({"phone_number": "Phone number is required."})

        # Safely check authentication before any role-based logic
        if not requesting_user or not getattr(requesting_user, 'is_authenticated', False):
            raise serializers.ValidationError("Authentication required.")

        # Permission logic applies only on CREATE (not update)
        if self.instance is None and not requesting_user.is_superuser:
            if requesting_user.is_manager:
                requested_stores = set(store.id for store in data.get('stores', []))
                manager_stores = set(requesting_user.stores.values_list('id', flat=True))
                print("DEBUG (validate):", requested_stores, manager_stores, requested_stores.issubset(manager_stores))

                if not requested_stores.issubset(manager_stores):
                    raise serializers.ValidationError(
                        "You can only create users for stores you manage."
                    )
            else:
                raise serializers.ValidationError("You don't have permission to create users.")

        return data

    def create(self, validated_data):
        print("INSIDE CREATE METHOD")
        request = self.context.get('request')
        requesting_user = request.user if request else None

        stores = validated_data.pop('stores', [])
        password = validated_data.pop('password', None)

        # Check if password is provided
        if not password:
            raise serializers.ValidationError({"password": "Password is required."})

        # Password strength validation
        if len(password) < 8:
            raise serializers.ValidationError({"password": "Password must be at least 8 characters long."})

        if not re.search(r'[A-Za-z]', password):
            raise serializers.ValidationError({"password": "Password must contain at least one letter."})

        if not re.search(r'\d', password):
            raise serializers.ValidationError({"password": "Password must contain at least one number."})

        # (Optional) Uncomment below if you want to require a special character:
        # if not re.search(r'[@$!%*?&#]', password):
        #     raise serializers.ValidationError({"password": "Password must contain at least one special character (@$!%*?&#)."})

        # Create user safely
        user = get_user_model().objects.create(**validated_data)
        user.set_password(password)
        user.stores.set(stores)

        try:
            user.generate_verification_token()
            send_verification_sms(user)
        except Exception as e:
            print(f"Warning: Failed to send verification SMS to {user.phone_number}: {str(e)}")

        return user
