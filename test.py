from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

from accounts.models import User
from stores.models import Store
from orders.models import Order


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

        self.store = Store.objects.create(name="Test Store")
        self.store.store_users.add(self.user)

        # Generate JWT token for the user
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        # Add the token to the header for authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

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
        store.store_users.add(self.admin)
        # store.store_users.add(self.user)  # Adjust based on actual model
        self.authenticate(self.admin)

        response = self.client.get("/api/users/me/stores/")
        # grabbing stores per user
        print(response)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_order(self):


        ######################
        # Order Creation
        ######################
        url = '/api/orders/'

        payload = {
            "store_id": self.store.id,
            "first_name": "LANDRY",
            "last_name": "ARGABRIGHT",
            "phone_num": "4692478210",
            "address": "456 Another St",
            "customer_email": "jane@example.com",
            "customer_num": "C123",
            "preferred_delivery_time": "10:00",
            "delivery_instructions": "Leave by garage",
            "notes": "Please handle with care",
            "delivery_date": timezone.now().date().isoformat(),
            "hasImage": False,
            "products": [  # Optional items, if your API expects them
                {
                    "product_name": "Sample Product",
                    "quantity": 2,
                    "price": 9.99,
                    "product_mpn": "SKU123"
                }
            ]
        }

        response = self.client.post(url, payload, format='json')

        # Debug output if needed
        print("RESPONSE:", response.status_code, response.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['store'], self.store.id)
        self.assertEqual(response.data['first_name'], "LANDRY")

        ######################
        # Order Update & Delete
        ######################
        



        ######################
        # Order Photos
        ######################


        ######################
        # Delivery Attempts:
        #   Status Changes (Driver Actions)
        ######################


        ######################
        # Delivery Attempts:
        #   Status Changes for 2nd + Attempts
        #   Scheduled Items for 2nd + Attempts
        ######################


        ######################
        # Messaging Templates
        ######################


        ######################
        # Messaging Triggers (Driver actions) & On/Off
        ######################