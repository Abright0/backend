# backend/api/views.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken, BlacklistMixin, TokenError

from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from django.conf import settings

import logging
logger = logging.getLogger(__name__)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'username': self.user.username,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'is_superuser': self.user.is_superuser,
            'is_store_manager': self.user.is_store_manager,
            'is_warehouse_manager': self.user.is_warehouse_manager,
            'is_inside_manager': self.user.is_inside_manager,
            'is_driver': self.user.is_driver,
            'is_customer_service': self.user.is_customer_service
        }
        return data
        
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        refresh = data.get('refresh')
        access = data.get('access')
        user = data.get('user')

        response = Response({
            'access': access,
            'user': user
        }, status=status.HTTP_200_OK)

        if refresh:
            response.set_cookie(
                key='refresh',
                value=refresh,
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Lax',  # not Strict
                path='/'
            )

        return response

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh')

        if not refresh_token:
            return Response({"error": "Refresh token cookie not found."}, status=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response({"error": "Invalid or expired refresh token."}, status=400)

        response = Response({"detail": "Logout successful."}, status=200)
        response.delete_cookie(
            'refresh',
            path='/',
            samesite='Lax'  # Optional, safe
        )
        return response