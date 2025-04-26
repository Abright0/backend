from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User
from stores.models import Store
from orders.models import Order, OrderItem
from assignments.models import DeliveryAttempt, ScheduledItem
from messaging.models import MessageTemplate

import itertools
import random

from PIL import Image
from io import BytesIO
from datetime import time

import pillow_heif
pillow_heif.register_heif_opener()

from unittest.mock import patch

import uuid
from django.conf import settings


class AccountsTestCase(APITestCase):
    def setUp(self):
        # Create test users
        self.superuser = User.objects.create_superuser(
            username='superadmin',
            email='super@example.com',
            password='SuperPass123',
            phone_number='5555555555'
        )

        self.manager = User.objects.create_user(
            username='manager1',
            email='manager1@example.com',
            password='ManagerPass123',
            phone_number='5555555556',
            is_manager=True
        )

        self.store_user = User.objects.create_user(
            username='storeuser1',
            email='user1@example.com',
            password='UserPass123',
            phone_number='5555555557'
        )

        # Link store_user to manager's store (assuming store relation exists)
        self.store = self.manager.stores.first() if self.manager.stores.exists() else None
        if self.store:
            self.store_user.stores.add(self.store)

        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='OtherPass123',
            phone_number='5555555558'
        )

    def test_register_password_strength(self):
        print("test_register_password_strength")
        url = reverse('user-register')  # Adjust this if your route name is different

        weak_password_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "123",
            "phone_number": "5555555559",
            "stores": []
        }

        # Authenticate as superuser
        self.client.force_authenticate(user=self.superuser)

        response = self.client.post(url, weak_password_data)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)


    def test_reset_password_success(self):
        print("test_reset_password_success")
        # Generate token manually for testing
        token = str(uuid.uuid4())
        self.store_user.password_reset_token = token
        self.store_user.password_reset_token_created_at = timezone.now()
        self.store_user.save()

        url = reverse('user-reset-password')
        data = {
            "token": token,
            "new_password": "NewSecurePass123"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.store_user.refresh_from_db()
        self.assertTrue(self.store_user.check_password("NewSecurePass123"))

    def test_reset_password_reuse_blocked(self):
        print("test_reset_password_reuse_blocked")
        token = str(uuid.uuid4())
        self.store_user.password_reset_token = token
        self.store_user.password_reset_token_created_at = timezone.now()
        self.store_user.save()

        url = reverse('user-reset-password')
        data = {
            "token": token,
            "new_password": "UserPass123"  # Same as old password!
        }
        response = self.client.post(url, data)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('New password cannot be the same as the old password.', str(response.data))

    def test_verify_phone_token_success(self):
        print("test_verify_phone_token_success")
        token = str(uuid.uuid4())
        self.store_user.phone_verification_token = token
        self.store_user.is_phone_verified = False
        self.store_user.save()

        url = reverse('verify-phone') + f'?token={token}'
        response = self.client.get(url)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.store_user.refresh_from_db()
        self.assertTrue(self.store_user.is_phone_verified)

    def test_update_profile_self_allowed(self):
        print("test_update_profile_self_allowed")
        self.client.force_authenticate(user=self.store_user)
        url = reverse('user-update-profile', kwargs={'pk': self.store_user.pk})
        response = self.client.patch(url, {'first_name': 'UpdatedName'})
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'UpdatedName')

    def test_update_profile_manager_allowed_for_own_user(self):
        print("test_update_profile_manager_allowed_for_own_user")
        self.client.force_authenticate(user=self.manager)
        url = reverse('user-update-profile', kwargs={'pk': self.store_user.pk})
        response = self.client.patch(url, {'first_name': 'ManagerUpdated'})
        if self.store:  # Only run if store relation exists
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['first_name'], 'ManagerUpdated')

    def test_update_profile_manager_denied_for_other_user(self):
        print("test_update_profile_manager_denied_for_other_user")
        self.client.force_authenticate(user=self.manager)
        url = reverse('user-update-profile', kwargs={'pk': self.other_user.pk})
        response = self.client.patch(url, {'first_name': 'ShouldNotWork'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_profile_superuser_can_update_anyone(self):
        print("test_update_profile_superuser_can_update_anyone")
        self.client.force_authenticate(user=self.superuser)
        url = reverse('user-update-profile', kwargs={'pk': self.other_user.pk})
        response = self.client.patch(url, {'first_name': 'SuperUpdated'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'SuperUpdated')

    def test_password_reset_rate_limit(self):
        print("test_password_reset_rate_limit")
        url = reverse('user-request-password-reset')
        for _ in range(4):  # Assuming the limit is 3/hour
            response = self.client.post(url, {'phone_number': self.other_user.phone_number})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class UserRegistrationSMSTest(APITestCase):
    def setUp(self):
        # Create a store for testing
        self.store = Store.objects.create(name="Test Store")

        # Superuser
        self.admin_user = User.objects.create_superuser(
            username="admin", 
            email="admin@example.com", 
            password="adminpass",
            phone_number="+1234567890"
        )

        # Manager with access to the store
        self.manager_user = User.objects.create_user(
            username="manager", 
            email="manager@example.com", 
            password="managerpass",
            phone_number="+1234567891",
            is_manager=True
        )
        self.manager_user.stores.add(self.store)

        self.register_url = reverse('user-register')

    def authenticate(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

    @patch('api.accounts.serializers.send_verification_sms')
    def test_superuser_can_create_user_for_any_store(self, mock_send_sms):
        print("test_superuser_can_create_user_for_any_store")
        """
        Superusers should be able to create users for any store.
        """
        other_store = Store.objects.create(name="Global Store")
        self.authenticate(self.admin_user)

        payload = {
            "username": "globaluser",
            "email": "global@example.com",
            "password": "globalpass",
            "first_name": "Global",
            "last_name": "User",
            "phone_number": "+1234567894",
            "stores": [other_store.id]
        }

        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="globaluser").exists())
        mock_send_sms.assert_called_once()

    @patch('api.accounts.serializers.send_verification_sms')
    def test_manager_can_only_assign_user_to_their_own_stores(self, mock_send_sms):
        print("test_manager_can_only_assign_user_to_their_own_stores")
        """
        Managers should only be able to create users for their assigned stores.
        """
        self.authenticate(self.manager_user)

        payload = {
            "username": "userforstore",
            "email": "userforstore@example.com",
            "password": "userpass",
            "first_name": "Store",
            "last_name": "User",
            "phone_number": "+1234567892",
            "stores": [self.store.id]  # Manager's own store
        }

        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="userforstore").exists())
        mock_send_sms.assert_called_once()

    @patch('api.accounts.serializers.send_verification_sms')
    def test_manager_cannot_assign_user_to_other_stores(self, mock_send_sms):
        print("test_manager_cannot_assign_user_to_other_stores")
        """
        Managers should NOT be able to create users for stores they don't manage.
        """
        other_store = Store.objects.create(name="Other Store")
        self.authenticate(self.manager_user)

        payload = {
            "username": "otherstoreuser",
            "email": "other@example.com",
            "password": "otherpass",
            "first_name": "Other",
            "last_name": "Store",
            "phone_number": "+1234567893",
            "stores": [other_store.id]  # store manager does NOT manage
        }

        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("You can only create users for stores you manage", str(response.data))
        self.assertFalse(User.objects.filter(username="otherstoreuser").exists())
        mock_send_sms.assert_not_called()

    @patch('api.accounts.serializers.send_verification_sms')
    def test_create_user_missing_phone_number_fails(self, mock_send_sms):
        print("test_create_user_missing_phone_number_fails")
        """
        User creation should fail if phone number is missing.
        """
        self.authenticate(self.admin_user)  # Superuser authenticated

        payload = {
            "username": "nopho",
            "email": "nopho@example.com",
            "password": "nopass",
            "first_name": "No",
            "last_name": "Phone",
            "stores": [self.store.id]
        }

        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="nopho").exists())
        mock_send_sms.assert_not_called()

"""
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
        #Helper to authenticate client
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
        # Message Template
        ######################

        event_template_map = {
            "order_placed": "Hey {{ customer_name }}, your order {{ order_id }} has been placed successfully!",
            "assigned_to_driver": "Your order {{ order_id }} has been assigned to a driver.",
            "accepted_by_driver": "The driver is preparing for your delivery (Order: {{ order_id }}).",
            "driver_en_route": "Heads up {{ customer_name }}! Your driver is en route with order {{ order_id }}. ETA: {{ mins_to_arrival }} mins, {{ miles_to_arrival }} miles away.",
            "driver_complete": "Your delivery for order {{ order_id }} is complete. View photos: {{ photo_links }}",
            "driver_misdelivery": "There was a delivery issue with order {{ order_id }}. Please contact support.",
            "driver_rescheduled": "Your delivery for order {{ order_id }} has been rescheduled.",
            "driver_canceled": "Your delivery for order {{ order_id }} has been canceled.",
        }
        for event, content in event_template_map.items():
            obj, created = MessageTemplate.objects.get_or_create(
                event=event,
                store=self.store,
                defaults={
                    "content": content,
                    "active": True,
                }
            )
            if created:
                print(f"Created template for event: {event}")
            else:
                print(f"Template already exists for event: {event}")

        ######################
        # Order Creation
        ######################
        url = f'/api/stores/{self.store.id}/orders/'  # updated

        payload = {
            "first_name": "LANDRY",
            "last_name": "ARGABRIGHT",
            "phone_num": "4692478210",
            "invoice_num":"kl89",
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
        update_url = f"/api/stores/{self.store.id}/orders/{order_id}/"  # 🔄 updated
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
        common_extensions = [
            ("jpg", "image/jpeg", "JPEG"),
            ("png", "image/png", "PNG"),
            ("webp", "image/webp", "WEBP"),
            ("heic", "image/heic", "HEIC")
        ]
        ext_cycle = itertools.cycle(common_extensions)

        # Step 1: Create initial delivery attempt
        da_url = f'/api/stores/{self.store.id}/orders/{order_id}/delivery-attempts/'  # 🔄 updated
        initial_payload = {
            "status": 'order_placed',
            "delivery_date": delivery_date,
            "delivery_time": time(hour=10, minute=0).isoformat(),
            "drivers": [self.driver.id],
        }
        da_response = self.client.post(da_url, initial_payload, format='json')
        self.assertEqual(da_response.status_code, status.HTTP_201_CREATED)
        delivery_attempt_id = da_response.data['id']

        # Step 2: Update delivery attempt through each status (except 'complete')
        for i, (status_code, _) in enumerate(DeliveryAttempt.STATUS_CHOICES):
            if status_code == 'complete':
                continue

            update_payload = {
                "status": status_code,
                "delivery_date": delivery_date,
                "delivery_time": time(hour=10 + i % 8, minute=0).isoformat(),
                "drivers": [self.driver.id],
            }

            if status_code == 'en_route':
                update_payload["mins_to_arrival"] = 15
                update_payload["miles_to_arrival"] = 3.5

            update_url = f'/api/stores/{self.store.id}/orders/{order_id}/delivery-attempts/{delivery_attempt_id}/'  #
            update_response = self.client.patch(update_url, update_payload, format='json')
            #print("UPDATE RESPONSE")
            #print(update_response.data)

            self.assertEqual(update_response.status_code, status.HTTP_200_OK)
            self.assertEqual(update_response.data['status'], status_code)

            # Generate and upload images
            images = []
            for photo_index in range(2):
                ext, mime, pil_format = next(ext_cycle)
                img = Image.new('RGB', (100, 100), color=(i * 40 % 255, photo_index * 120, 150))
                buffer = BytesIO()

                if pil_format == "HEIC":
                    img.save(buffer, format="HEIF")
                else:
                    img.save(buffer, format=pil_format)

                buffer.seek(0)
                filename = f"{status_code}_photo{photo_index + 1}.{ext}"
                image_file = SimpleUploadedFile(filename, buffer.read(), content_type=mime)
                images.append(image_file)

            photo_url = f'/api/stores/{self.store.id}/orders/{order_id}/delivery-attempts/{delivery_attempt_id}/photos/'  #
            photo_response = self.client.post(photo_url, {
                'images': images,
                'delivery_attempt': delivery_attempt_id,
                'caption': f'{status_code} photos',
            }, format='multipart')

            self.assertEqual(photo_response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(len(photo_response.data), 2)
            for photo in photo_response.data:
                self.assertIn('signed_url', photo)


        final_update_url = f'/api/stores/{self.store.id}/orders/{order_id}/delivery-attempts/{delivery_attempt_id}/'
        final_update_payload = {"status": 'complete'}

        # Step 3-A: Ensure template is active → should trigger SMS
        print("\n--- TESTING: Template is ACTIVE ---")
        msg_template = MessageTemplate.objects.get(store=self.store, event='driver_complete')
        msg_template.active = True
        msg_template.save()

        with self.captureOnCommitCallbacks(execute=True):  # Makes sure post-commit actions (like send_sms) run in tests
            response_active = self.client.patch(final_update_url, final_update_payload, format='json')
            self.assertEqual(response_active.status_code, status.HTTP_200_OK)
            self.assertEqual(response_active.data['status'], 'complete')

        # Step 3-B: Set template to inactive → SMS should not trigger
        # Reset status to 'en_route' first
        print("\n--- TESTING: Template is INACTIVE ---")
        rollback_payload = {
            "status": "en_route",
            "delivery_date": delivery_date,
            "delivery_time": time(hour=11).isoformat(),
            "drivers": [self.driver.id],
        }
        self.client.patch(final_update_url, rollback_payload, format='json')

        # Deactivate the template
        msg_template.active = False
        msg_template.save()

        # Try to complete again
        with self.captureOnCommitCallbacks(execute=True):
            response_inactive = self.client.patch(final_update_url, final_update_payload, format='json')
            self.assertEqual(response_inactive.status_code, status.HTTP_200_OK)
            self.assertEqual(response_inactive.data['status'], 'complete')


        # Step 4: Schedule order items
        order_items = OrderItem.objects.filter(order_id=order_id)
        self.assertTrue(order_items.exists(), "No order items found for this order")

        for item in order_items:
            scheduled = ScheduledItem.objects.create(
                delivery_attempt_id=delivery_attempt_id,
                order_item=item,
                quantity=min(1, item.quantity)
            )
            print(f"ScheduledItem: {scheduled}")
"""

        ######################
        # GET RANDOM PHOTOS
        ######################
"""
        import random
        from assignments.models import DeliveryAttempt, DeliveryPhoto

        # Get all attempts for this order
        delivery_attempts = DeliveryAttempt.objects.filter(order_id=order_id)

        # Randomly pick one
        random_attempt = random.choice(list(delivery_attempts))
        print(f"🔍 Chosen attempt ID: {random_attempt.id} — Status: {random_attempt.status}")

        # Get all photos for this attempt
        photos = DeliveryPhoto.objects.filter(delivery_attempt=random_attempt)

        # Print photo info
        for photo in photos:
            print(f"📸 Photo ID: {photo.id}, Caption: {photo.caption}, Image: {photo.image.url}")
"""