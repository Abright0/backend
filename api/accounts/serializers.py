from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from accounts.models import User
from stores.models import Store
from .utils import send_verification_sms, send_reset_sms, check_reset_code

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
            'is_store_manager',
            'is_warehouse_manager',
            'is_inside_manager',
            'is_active',
            'is_superuser',
            'date_joined',
            'stores',
            'is_phone_verified',
            'roles',
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': False, 'allow_null': True, 'allow_blank': True},
        }
    def get_roles(self, obj):
        return obj.get_roles()

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, data):
        request = self.context.get('request')
        requesting_user = request.user if request else None

        if self.instance is None and not data.get('phone_number'):
            raise serializers.ValidationError({"phone_number": "Phone number is required."})

        if not requesting_user or not getattr(requesting_user, 'is_authenticated', False):
            raise serializers.ValidationError("Authentication required.")

        self._validate_roles(data, requesting_user)
        self._validate_store_permissions(data, requesting_user)
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        stores = validated_data.pop('stores', [])
        password = validated_data.pop('password', None)

        if not password:
            raise serializers.ValidationError({"password": "Password is required."})

        self.validate_password(password)

        user = get_user_model().objects.create(**validated_data)
        user.set_password(password)
        user.stores.set(stores)

        try:
            user.generate_verification_token()
            send_verification_sms(user)
        except Exception as e:
            print(f"Warning: Failed to send verification SMS to {user.phone_number}: {str(e)}")

        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        stores = validated_data.pop('stores', None)

        user = super().update(instance, validated_data)

        if password:
            self.validate_password(password)
            user.set_password(password)
            user.save()

        if stores is not None:
            user.stores.set(stores)

        return user

    def _validate_roles(self, data, requesting_user):
        role_fields = [
            'is_store_manager', 
            'is_warehouse_manager', 
            'is_inside_manager', 
            'is_driver', 
            'is_customer_service',
            'is_superuser'
        ]
        incoming_roles = {field: data.get(field) for field in role_fields if field in data}

        if incoming_roles:
            if requesting_user.is_superuser:
                return
            elif requesting_user.is_store_manager or requesting_user.is_warehouse_manager or requesting_user.is_inside_manager:
                if incoming_roles.get('is_superuser'):
                    raise serializers.ValidationError(
                        {"roles": "Store-level managers cannot assign superuser roles."}
                    )
            else:
                raise serializers.ValidationError(
                    {"roles": "You do not have permission to assign or modify roles."}
                )

        if self.instance and self.instance == requesting_user and incoming_roles:
            if not requesting_user.is_superuser:
                raise serializers.ValidationError({"roles": "You cannot modify your own role assignments."})

    def _validate_store_permissions(self, data, requesting_user):
        if self.instance is None and not requesting_user.is_superuser:
            if requesting_user.is_store_manager or requesting_user.is_warehouse_manager or requesting_user.is_inside_manager:
                requested_stores = set(store.id for store in data.get('stores', []))
                manager_stores = set(requesting_user.stores.values_list('id', flat=True))
                if not requested_stores.issubset(manager_stores):
                    raise serializers.ValidationError(
                        "You can only create users for stores you manage."
                    )
            else:
                raise serializers.ValidationError("You don't have permission to create users.")

class ResetPasswordRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate_phone_number(self, value):
        try:
            self.user = User.objects.get(phone_number=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this phone number does not exist.")
        return value

    def save(self):
        success = send_reset_sms(self.user)
        if not success:
            raise serializers.ValidationError("Failed to send reset code.")
        return True


class ResetPasswordConfirmSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            user = User.objects.get(phone_number=data['phone_number'])
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid phone number.")

        if not check_reset_code(user, data['code']):
            raise serializers.ValidationError("Invalid or expired code.")

        try:
            validate_password(data['new_password'], user)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": e.messages})

        data['user'] = user
        return data

    def save(self):
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        return user