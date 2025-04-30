from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
import uuid
import re

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from .serializers import (
    UserSerializer,
    ResetPasswordRequestSerializer,
    ResetPasswordConfirmSerializer
)
from api.stores.serializers import StoreSerializer
from api.accounts.utils import send_verification_sms
from api.accounts.throttles import PasswordResetRateThrottle, VerificationResendRateThrottle


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

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
            return Response({"detail": "Invalid verification token"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def stores(self, request, pk=None):
        user = self.get_object()
        stores = user.stores.all()
        serializer = StoreSerializer(stores, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def update_profile(self, request, pk=None):
        user = self.get_object()

        if user != request.user and not request.user.is_superuser:
            if request.user.is_manager:
                manager_store_ids = request.user.stores.values_list('id', flat=True)
                target_store_ids = user.stores.values_list('id', flat=True)
                if not set(target_store_ids).intersection(manager_store_ids):
                    return Response(
                        {'error': 'You can only update users in your managed stores.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                return Response({'error': 'You do not have permission to update this profile.'},
                                status=status.HTTP_403_FORBIDDEN)

        serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({"detail": "You do not have permission to access this resource"},
                            status=status.HTTP_403_FORBIDDEN)
        users = User.objects.all()
        verification_status = {user.id: user.is_email_verified for user in users}
        return Response(verification_status)

    @action(detail=True, methods=['post'], throttle_classes=[VerificationResendRateThrottle])
    def resend_verification(self, request, pk=None):
        if not (request.user.is_superuser or request.user.is_manager):
            return Response({"detail": "You do not have permission to access this resource"},
                            status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        if user.is_email_verified:
            return Response({"detail": "User is already verified"}, status=status.HTTP_400_BAD_REQUEST)
        token = user.generate_verification_token()
        send_verification_sms(user)
        return Response({
            "detail": f"Verification SMS resent to {user.phone_number}",
            "user_id": user.id,
            "phone_number": user.phone_number
        })

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='me/stores')
    def my_stores(self, request):
        stores = request.user.stores.all()
        serializer = StoreSerializer(stores, many=True)
        return Response(serializer.data)


class PasswordResetCodeRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = ResetPasswordRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Verification code sent via SMS"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetCodeConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordConfirmSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Password successfully reset"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyPhoneView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token')
        if not token:
            return Response({"detail": "Verification token is required."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(phone_verification_token=token)
            if not user.is_phone_verified:
                user.is_phone_verified = True
                user.save()
                return Response({"detail": "Phone successfully verified via SMS"})
            return Response({"detail": "Phone already verified"})
        except User.DoesNotExist:
            return Response({"detail": "Invalid verification token"}, status=status.HTTP_400_BAD_REQUEST)
