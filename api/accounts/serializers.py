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
    roles = serializers.SerializerMethodField()

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
            'is_phone_verified',
            'roles',
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def get_roles(self, obj):
        return obj.get_roles()

    def validate(self, data):
        request = self.context.get('request')
        requesting_user = request.user if request else None

        if self.instance is None and not data.get('phone_number'):
            raise serializers.ValidationError({"phone_number": "Phone number is required."})

        if not requesting_user or not getattr(requesting_user, 'is_authenticated', False):
            raise serializers.ValidationError("Authentication required.")

        # ROLE VALIDATION STARTS HERE:
        role_fields = ['is_manager', 'is_customer_service', 'is_driver', 'is_superuser']
        incoming_roles = {field: data.get(field) for field in role_fields if field in data}

        if incoming_roles:
            if requesting_user.is_superuser:
                # Superuser can assign anything, including superuser
                pass
            elif requesting_user.is_manager:
                # Managers cannot assign manager or superuser roles
                if incoming_roles.get('is_manager') or incoming_roles.get('is_superuser'):
                    raise serializers.ValidationError(
                        {"roles": "Managers cannot assign 'manager' or 'superuser' roles."}
                    )
            else:
                raise serializers.ValidationError(
                    {"roles": "You do not have permission to assign or modify roles."}
                )

        # Prevent users from modifying their own roles (optional but recommended):
        if self.instance and self.instance == requesting_user and incoming_roles:
            if not requesting_user.is_superuser:  # Superuser can modify their own roles
                raise serializers.ValidationError({"roles": "You cannot modify your own role assignments."})

        # Existing CREATE logic (for store restrictions):
        if self.instance is None and not requesting_user.is_superuser:
            if requesting_user.is_manager:
                requested_stores = set(store.id for store in data.get('stores', []))
                manager_stores = set(requesting_user.stores.values_list('id', flat=True))
                if not requested_stores.issubset(manager_stores):
                    raise serializers.ValidationError(
                        "You can only create users for stores you manage."
                    )
            else:
                raise serializers.ValidationError("You don't have permission to create users.")

        return data