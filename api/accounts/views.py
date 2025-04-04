# backend/api/accounts/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone


from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from api.accounts.utils import send_reset_email
from accounts.models import User
from .serializers import UserSerializer
from api.stores.serializers import StoreSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    """
    Helper Methods
    """
    # Verify email
    @action(detail=False, methods=['get'],permission_classes=[AllowAny])
    def verify_email(self, request):
        token = request.query_params.get('token')
        print(token)
        print(type(token))

        try:
            user = User.objects.get(email_verification_token=token)
            if not user.is_email_verified:
                user.is_email_verified = True
                user.save()
                return Response({"detail": "Email successfully verified"})
            return Response({"detail": "Email already verified"})
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid verification token"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    # Get all Stores for a specific user
    @action(detail=True, methods=['get'])
    def stores(self, request, pk=None):
        user = self.get_object()
        stores = user.stores.all()
        serializer = StoreSerializer(stores, many=True)
        return Response(serializer.data)

    # UPDATE PROFILE
    @action(detail=True, methods=['patch'])
    def update_profile(self, request, pk=None):
        user = self.get_object()
        
        # Optional: Ensure user can only update their own profile
        if user != request.user and not request.user.is_manager:
            return Response({
                'error': 'You can only update your own profile'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = UserSerializer(
            user, 
            data=request.data, 
            partial=True,  # Allow partial updates
            context={'request': request}  # Pass request to serializer
        )
        
        if serializer.is_valid():
            # Optional: Add custom validation or pre-save logic
            serializer.save()
            
            return Response(serializer.data)
        
        return Response(
            serializer.errors, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # Request Password Reset
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def request_password_reset(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            
            # Generate reset token
            reset_token = default_token_generator.make_token(user)
            
            # Optional: Set token expiration
            #user.password_reset_token = reset_token
            #user.password_reset_token_created_at = timezone.now()
            user.save()
            
            # Send reset email (implement email sending logic)
            send_reset_email(user=user, reset_token=reset_token)
            
            return Response({
                "detail": "Password reset link sent to your email",
                "token": reset_token  # For testing purposes
            })
        except User.DoesNotExist:
            return Response(
                {"detail": "No user found with this email"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    

    # Reset Password
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def reset_password(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        
        # Validate input
        if not token or not new_password:
            return Response(
                {"detail": "Token and new password are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(password_reset_token=token)
            
            # Check token expiration (optional)
            token_age = timezone.now() - user.password_reset_token_created_at
            if token_age.total_seconds() > 3600:  # 1 hour expiration
                return Response(
                    {"detail": "Token has expired"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate password (add your password complexity checks)
            if len(new_password) < 4:
                return Response(
                    {"detail": "Password too short"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set new password
            user.set_password(new_password)
            
            # Clear reset token
            user.password_reset_token = None
            user.password_reset_token_created_at = None
            user.save()
            
            return Response({"detail": "Password successfully reset"})
        
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid reset token"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def me(self, request):
        "Return the current user's profile"
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_stores(self, request):
        "Get stores for the current user"
        stores = request.user.stores.all()
        serializer = StoreSerializer(stores, many=True)
        return Response(serializer.data)
            
        # Add this to your UserViewSet class
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = UserSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            # Create the user
            user = serializer.save()
            
            # Generate verification token and send email
            token = user.generate_verification_token()
            send_verification_email(user)
            
            return Response({
                "detail": "User registered successfully. Please check your email to verify your account.",
                "user_id": user.id,
                "email": user.email
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


        # Add this to your UserViewSet class in backend/api/accounts/views.py

    @action(detail=False, methods=['get'])
    def email_verification_status(self, request):
        """
        Return email verification status for all users
        Only accessible to admins, managers and superusers
        """
        if not (request.user.is_superuser or request.user.is_manager):
            return Response(
                {"detail": "You do not have permission to access this resource"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        54
        # Query all users and return their ID and verification status
        users = User.objects.all()
        verification_status = {
            user.id: user.is_email_verified 
            for user in users
        }
        
        return Response(verification_status)
        # Add this to your UserViewSet class in backend/api/accounts/views.py

    @action(detail=True, methods=['post'])
    def resend_verification(self, request, pk=None):
        """
        Resend verification email to a user
        Only accessible to admins, managers and superusers
        """
        if not (request.user.is_superuser or request.user.is_manager):
            return Response(
                {"detail": "You do not have permission to access this resource"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        
        # Skip if already verified
        if user.is_email_verified:
            return Response(
                {"detail": "User email is already verified"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate new verification token
        token = user.generate_verification_token()
        
        # Send verification email
        from api.accounts.utils import send_verification_email
        send_verification_email(user)
        
        return Response({
            "detail": f"Verification email resent to {user.email}",
            "user_id": user.id,
            "email": user.email
        })