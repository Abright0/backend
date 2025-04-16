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
        store.users.add(self.user)  # Adjust based on actual model
        self.authenticate(self.user)

        response = self.client.get("/api/users/me/stores/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_register_user(self):
        store = Store.objects.create(name="Register Store")
        payload = {
            "email": "newuser@example.com",
            "username": "newuser123",
            "password": "newpassword123",
            "stores": [store.id]
        }
        response = self.client.post("/api/users/register/", data=payload)
        print(response.data)  # You can remove this after test passes
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user_id", response.data)

    def test_request_password_reset(self):
        payload = {"email": self.user.email}
        response = self.client.post("/api/users/request_password_reset/", data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_email_verification_status_admin(self):
        self.authenticate(self.admin)
        response = self.client.get("/api/users/email_verification_status/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_email_verification_status_forbidden(self):
        self.authenticate(self.user)
        response = self.client.get("/api/users/email_verification_status/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_resend_verification_as_admin(self):
        user = User.objects.create_user(username="user_2", email="verifyme@example.com", password="1234", is_email_verified=False)
        self.authenticate(self.admin)
        url = f"/api/users/{user.id}/resend_verification/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)

    def test_update_profile(self):
        self.authenticate(self.user)
        url = f"/api/users/{self.user.id}/update_profile/"
        data = {"first_name": "Updated"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Updated")
