# api/accounts/views.py
from django.shortcuts import get_object_or_404
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone

import uuid

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import User
from .serializers import UserSerializer
from api.stores.serializers import StoreSerializer
from api.accounts.utils import send_reset_sms, send_verification_sms
from api.accounts.throttles import PasswordResetRateThrottle, VerificationResendRateThrottle

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    # Verify phone via SMS
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def verify_sms(self, request):
        token = request.query_params.get('token')
        try:
            user = User.objects.get(email_verification_token=token)
            if not user.is_email_verified:
                user.is_email_verified = True
                user.save()
                return Response({"detail": "Phone successfully verified via SMS"})
            return Response({"detail": "Phone already verified"})
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid verification token"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def stores(self, request, pk=None):
        user = self.get_object()
        stores = user.stores.all()
        serializer = StoreSerializer(stores, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def update_profile(self, request, pk=None):
        user = self.get_object()

        # Permission Logic
        if user == request.user:
            pass  # Users can update their own profile
        elif request.user.is_superuser:
            pass  # Superusers can update anyone
        elif request.user.is_manager:
            manager_store_ids = request.user.stores.values_list('id', flat=True)
            target_store_ids = user.stores.values_list('id', flat=True)
            if not set(target_store_ids).intersection(manager_store_ids):
                return Response(
                    {'error': 'You can only update users in your managed stores.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            return Response(
                {'error': 'You do not have permission to update this profile.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Profile Update Logic
        serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




    # Request Password Reset via SMS
    @action(detail=False, methods=['post'], permission_classes=[AllowAny], throttle_classes=[PasswordResetRateThrottle])
    def request_password_reset(self, request):
        phone_number = request.data.get('phone_number')
        try:
            user = User.objects.get(phone_number=phone_number)
            reset_token = str(uuid.uuid4())

            # Send reset SMS (this also sets the token + timestamp)
            send_reset_sms(user=user, reset_token=reset_token)

            return_data = {
                "detail": "Password reset link sent via SMS"
            }

            if settings.DEBUG:
                return_data["token"] = reset_token  # Expose token only in development

            return Response(return_data)

        except User.DoesNotExist:
            return Response(
                {"detail": "No user found with this phone number"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def reset_password(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not token or not new_password:
            return Response(
                {"detail": "Token and new password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Password strength validation
        if len(new_password) < 8:
            return Response({"detail": "Password must be at least 8 characters long."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not re.search(r'[A-Za-z]', new_password):
            return Response({"detail": "Password must contain at least one letter."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not re.search(r'\d', new_password):
            return Response({"detail": "Password must contain at least one number."},
                            status=status.HTTP_400_BAD_REQUEST)

        # (Optional) Require a special character:
        # if not re.search(r'[@$!%*?&#]', new_password):
        #     return Response({"detail": "Password must contain at least one special character (@$!%*?&#)."},
        #                     status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(password_reset_token=token)
            token_age = timezone.now() - user.password_reset_token_created_at
            if token_age.total_seconds() > 3600:
                return Response({"detail": "Token has expired"}, status=status.HTTP_400_BAD_REQUEST)

            if user.check_password(new_password):
                return Response(
                    {"detail": "New password cannot be the same as the old password."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(new_password)
            user.password_reset_token = None
            user.password_reset_token_created_at = None
            user.save()

            return Response({"detail": "Password successfully reset"})

        except User.DoesNotExist:
            return Response({"detail": "Invalid reset token"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='me/stores')
    def my_stores(self, request):
        stores = request.user.stores.all()
        serializer = StoreSerializer(stores, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny],
        throttle_classes=[PasswordResetRateThrottle])
    def register(self, request):
        serializer = UserSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            token = user.generate_verification_token()
            send_verification_sms(user)
            return Response({
                "detail": "User registered successfully. Please check your phone for verification SMS.",
                "user_id": user.id,
                "phone_number": user.phone_number
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def sms_verification_status(self, request):
        if not (request.user.is_superuser or request.user.is_manager):
            return Response(
                {"detail": "You do not have permission to access this resource"},
                status=status.HTTP_403_FORBIDDEN
            )
        users = User.objects.all()
        verification_status = {user.id: user.is_email_verified for user in users}
        return Response(verification_status)

    @action(detail=True, methods=['post'], throttle_classes=[VerificationResendRateThrottle])
    def resend_verification(self, request, pk=None):
        if not (request.user.is_superuser or request.user.is_manager):
            return Response(
                {"detail": "You do not have permission to access this resource"},
                status=status.HTTP_403_FORBIDDEN
            )
        user = self.get_object()
        if user.is_email_verified:
            return Response(
                {"detail": "User is already verified"},
                status=status.HTTP_400_BAD_REQUEST
            )
        token = user.generate_verification_token()
        send_verification_sms(user)
        return Response({
            "detail": f"Verification SMS resent to {user.phone_number}",
            "user_id": user.id,
            "phone_number": user.phone_number
        })