from rest_framework import serializers
from accounts.models import User
from django.contrib.auth import get_user_model
from .utils import send_verification_email

from rest_framework_simplejwt.authentication import JWTAuthentication

class UserSerializer(serializers.ModelSerializer):
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
            'stores'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        """
        Create a new user with better error handling for email verification
        """
        # Get the request context
        request = self.context.get('request')
        
        # Check if the request is coming from the registration endpoint
        if request and request.path.endswith('/register/'):
            # For public registration, no special permissions needed
            stores = validated_data.pop('stores', [])
            user = get_user_model().objects.create_user(**validated_data)
            user.stores.set(stores)
            
            # Generate verification token
            user.generate_verification_token()
            
            # Try to send verification email but don't fail if it doesn't work
            try:
                send_verification_email(user)
            except Exception as e:
                print(f"Warning: Failed to send verification email to {user.email}: {str(e)}")
                # The user is still created even if email fails
                
            return user
        
        # For admin-created users, check permissions
        requesting_user = request.user if request else None
        
        if not requesting_user:
            raise serializers.ValidationError("Authentication required")
        
        # Handle job position-based permissions
        if requesting_user.is_superuser:
            # Superusers can create any user
            stores = validated_data.pop('stores', [])
            user = get_user_model().objects.create_user(**validated_data)
            user.stores.set(stores)
            
            # Try to send verification email but don't fail if it doesn't work
            try:
                user.generate_verification_token()
                send_verification_email(user)
            except Exception as e:
                print(f"Warning: Failed to send verification email to {user.email}: {str(e)}")
                # The user is still created even if email fails
                
            return user
        
        elif requesting_user.is_manager:
            # Managers can only create users for stores they manage
            requested_stores = set(validated_data.get('stores', []))
            manager_stores = set(requesting_user.stores.values_list('id', flat=True))

            if not requested_stores.issubset(manager_stores):
                raise serializers.ValidationError(
                    "You can only create users for stores you manage"
                )

            stores = validated_data.pop('stores', [])
            user = get_user_model().objects.create_user(**validated_data)
            user.stores.set(stores)
            
            # Try to send verification email but don't fail if it doesn't work
            try:
                user.generate_verification_token()
                send_verification_email(user)
            except Exception as e:
                print(f"Warning: Failed to send verification email to {user.email}: {str(e)}")
                # The user is still created even if email fails
                
            return user
        
        else:
            # Other users don't have permission to create users
            raise serializers.ValidationError(
                "You don't have permission to create users"
            )



"""
        jwt_auth = JWTAuthentication()

        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header:
            validated_token = jwt_auth.get_validated_token(auth_header.split(' ')[1])
            user = jwt_auth.get_user(validated_token)
            print("Authenticated user:", user)


        # Get the authenticated user making the request
        print("Printing Request")
        print(request)
        requesting_user = request.user
        print(requesting_user)
        if not requesting_user.is_manager:
            return Response({
                'error': 'Only managers can create new users'
            }, status=status.HTTP_403_FORBIDDEN)

        requested_stores = set(store.id for store in request.data.get('stores', []))
        manager_stores = set(requesting_user.stores.values_list('id', flat=True))
        
        if not requested_stores.issubset(manager_stores):
            return Response({
                'error': 'You can only create users for stores you manage'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        """