
# backend/api/views.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken, BlacklistMixin



from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


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
            'is_manager': self.user.is_manager,
            'is_driver': self.user.is_driver,
            'is_customer_service': self.user.is_customer_service
        }
        return data
        
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({"error": "No refresh token"}, status=400)
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=200)
        except Exception as e:
            print(f"Logout error: {str(e)}")
            return Response({"error": str(e)}, status=400)


            