from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from accounts.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from stores.models import Store


class UserViewSetTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username ="user",
            email="user@example.com",
            password="password123",
            is_email_verified=True
        )
        self.admin = User.objects.create_superuser(
            username ="user_1",
            email="admin@example.com",
            password="adminpass"
        )
        self.client = APIClient()

    def authenticate(self, user):
        """Helper to authenticate client"""
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

    def test_get_current_user_profile(self):
        self.authenticate(self.user)
        response = self.client.get("/api/users/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)

    def test_get_my_stores(self):
        store = Store.objects.create(name="Test Store")
         # store.store_users.add(self.user)  # Adjust based on actual model
        self.authenticate(self.user)

        response = self.client.get("/api/users/me/stores/")
        # grabbing stores per user
        print(response)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

