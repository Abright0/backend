from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile


from accounts.models import User
from stores.models import Store
from orders.models import Order
from assignments.models import DeliveryAttempt


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
        self.driver = User.objects.create_user(
            username ="driver_1",
            email="driver@example.com",
            password="adminpass",
            is_email_verified=True,
            is_driver=True
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
        #print(response)
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
            "products": [
                {
                    "product_name": "Sample Product",
                    "quantity": 2,
                    "price": 9.99,
                    "product_mpn": "SKU123"
                }
            ]
        }

        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['store'], self.store.id)
        self.assertEqual(response.data['first_name'], "LANDRY")
        order_id = response.data['id']
        delivery_date = response.data['delivery_date']

        ######################
        # Order Update
        ######################
        update_url = f"/api/orders/{order_id}/"
        update_payload = {
            "notes": "Updated note from test",
            "delivery_instructions": "updated instructions"
        }

        response = self.client.patch(update_url, update_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["notes"], "Updated note from test")
        self.assertEqual(response.data["delivery_instructions"], "updated instructions")

        ######################
        # DELIVERY ATTEMPT + PHOTO + STATUS CHECKS
        ######################
        from assignments.models import DeliveryAttempt
        for status_code, _ in DeliveryAttempt.STATUS_CHOICES:
            da_url = f'/api/orders/{order_id}/delivery-attempts/'
            da_payload = {
                "status": status_code,
                "delivery_date": delivery_date,
                "drivers": [self.driver.id]
            }
            da_response = self.client.post(da_url, da_payload, format='json')
            self.assertEqual(da_response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(da_response.data['status'], status_code)
            delivery_attempt_id = da_response.data['id']

            # Upload a photo for each delivery attempt
            photo_url = f'/api/orders/{order_id}/delivery-attempts/{delivery_attempt_id}/photos/'
            image_data = SimpleUploadedFile("test.jpg", b"file_content", content_type="image/jpeg")
            response = self.client.post(photo_url, {
                'images': [image_data],
                'delivery_attempt': delivery_attempt_id,
                'caption': f'Photo for status {status_code}',
            }, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(len(response.data), 1)
            self.assertIn('signed_url', response.data[0])

        ######################
        # Order Delete
        ######################
        delete_url = f'/api/orders/{order_id}/'
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(id=order_id).exists())
