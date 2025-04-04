from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from products.models import Product
from stores.models import Store
from orders.models import Order
from assignments.models import Assignment  # Updated from 'deliveries' to 'assignments'
from datetime import date, time
from accounts.models import User

class AssignmentTests(APITestCase):

    def setUp(self):
        
        # Admin user setup
        self.admin_user = User.objects.create(
            username='ADMIN',
            email='ADMIN@ADMIN.com',    
            is_manager=True,
            is_driver=True
        )

        # Create a user (driver) for assignment
        self.user = get_user_model().objects.create_user(
            username='driver1', password='password123', email="test2@mail.com"
        )
        
        # Create test products
        self.product1 = Product.objects.create(name="Test Product 1", price=10.99, quantity=2)
        self.product2 = Product.objects.create(name="Test Product 2", price=20.99, quantity=3)

        # Create another driver
        self.driver2 = get_user_model().objects.create_user(
            username='driver2', password='password123', email="test3@mail.com"
        )
        
        self.store = Store.objects.create(name="Test Store")

        # Prepare client for API requests
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

        # Create an order via the API and set the order_id
        self.test_order_creation()

    def test_order_creation(self):
        
        # Test creating an order through the API and saving the order ID for later use.
        
        url = '/api/orders/'  # Assume this is the order creation URL
        data = {
            "store": self.store.id,
            "first_name": "John",
            "last_name": "Doe",
            "phone_num": "+1234567890",
            "address": "123 Test St",
            "customer_email": "test@example.com",
            "customer_num": "CUST001",
            "preferred_delivery_time": "14:00:00",
            "delivery_instructions": "Leave at door",
            "notes": "Test order",
            "invoice_num": "1234",
            "items": [
                {"product_name_input": self.product1.name, "product_name":self.product1.name, "quantity": 2, "price_at_order":self.product1.price},
                {"product_name_input": self.product2.name, "product_name":self.product2.name, "quantity": 3, "price_at_order":self.product2.price}
            ]
        }

        response = self.client.post(url, data, format='json')
        
        # Save the order ID for future tests
        self.order_id = response.data['id']
        print("self order id")
        print(self.order_id)
        # Validate the response
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['first_name'], 'John')
        self.assertEqual(response.data['address'], '123 Test St')
        self.assertEqual(response.data['customer_email'], 'test@example.com')
        

    def test_assignment_creation(self):
        """
        Test assigning drivers to an order and creating an assignment using an order created via API.
        """
        url = '/api/assignments/'  # This is the assignment creation URL (ensure it's correct for your setup)
        data = {
            'order': self.order_id,  # Use the order ID from the API creation
            'drivers': [self.user.id, self.driver2.id],
            'assigned_delivery_date': str(date.today()),
            'assigned_delivery_time': str(time(10, 30)),
            'status': 'order_placed'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['order'], self.order_id)
        self.assertEqual(len(response.data['drivers']), 2)
        self.assertEqual(response.data['status'], 'order_placed')
        self.assertEqual(response.data['assigned_delivery_date'], str(date.today()))
        self.assertEqual(response.data['assigned_delivery_time'], '10:30:00')

    def test_status_change_and_logging(self):
        """
        Test changing the status of an assignment and ensuring history is logged.
        """
        # First, create an assignment
        assignment = Assignment.objects.create(
            order_id=self.order_id,  # Use the order ID from the API creation
            status='order_placed',
            assigned_delivery_date=date.today(),
            assigned_delivery_time=time(10, 30)
        )
        assignment.drivers.set([self.user, self.driver2])  # Assign drivers

        # Log history
        assignment.add_to_history(
            status='order_placed',
            delivery_date=date.today(),
            delivery_time=time(10, 30),
            result='Assignment created',
            drivers=[self.user, self.driver2]
        )

        # Change the status to 'accepted_by_driver'
        assignment.status = 'accepted_by_driver'
        assignment.save()

        # Log history
        assignment.add_to_history(
            status='accepted_by_driver',
            delivery_date=date.today(),
            delivery_time=time(10, 30),
            result='Driver accepted the assignment',
            drivers=[self.user, self.driver2]
        )

        # Test that history contains the changes
        self.assertEqual(len(assignment.previous_assignments), 2)
        self.assertEqual(assignment.previous_assignments[1]['status'], 'accepted_by_driver')
        self.assertEqual(assignment.previous_assignments[1]['result'], 'Driver accepted the assignment')

    def test_status_change_and_assignment_update(self):
        """
        Test changing assignment status through API.
        """
        # Create the assignment via API
        url = '/api/assignments/'
        data = {
            'order': self.order_id,  # Use the order ID from the API creation
            'drivers': [self.user.id],
            'assigned_delivery_date': str(date.today()),
            'assigned_delivery_time': '14:00:00',
            'status': 'order_placed'
        }
        response = self.client.post(url, data, format='json')

        print('output from assignments API POST')
        print(response.data)
        assignment_id = response.data['id']
        self.assertEqual(response.status_code, 201)

        # Update the assignment's status through API
        update_url = f'/api/assignments/{assignment_id}/'  # URL for specific assignment
        updated_data = {'status': 'in_progress'}
        update_response = self.client.patch(update_url, updated_data, format='json')

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data['status'], 'in_progress')

        # Ensure history is logged by checking the response of the updated assignment
        assignment = Assignment.objects.get(id=assignment_id)
        self.assertEqual(len(assignment.previous_assignments), 2)  # The status change should be recorded
        self.assertEqual(assignment.previous_assignments[0]['status'], 'order_placed')
        self.assertEqual(assignment.previous_assignments[0]['result'], 'Assignment created')

    def test_redelivery_workflow(self):
        """
        Test the complete redelivery workflow:
        1. Create initial assignment
        2. Mark as misdelivery
        3. Assign for redelivery with new drivers
        4. Complete redelivery process
        """
        # Create initial assignment
        url = '/api/assignments/'
        initial_data = {
            'order': self.order_id,
            'drivers': [self.user.id],  # Initial driver
            'assigned_delivery_date': str(date.today()),
            'assigned_delivery_time': '14:00:00',
            'status': 'order_placed'
        }
        response = self.client.post(url, initial_data, format='json')
        assignment_id = response.data['id']
        self.assertEqual(response.status_code, 201)

        # Mark as misdelivery
        update_url = f'/api/assignments/{assignment_id}/'
        misdelivery_data = {'status': 'misdelivery'}
        response = self.client.patch(update_url, misdelivery_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'misdelivery')

        # Assign for redelivery with new drivers
        redelivery_data = {
            'status': 'redelivery_assigned',
            'drivers': [self.driver2.id],  # New driver for redelivery
            'assigned_delivery_date': str(date.today()),
            'assigned_delivery_time': '16:00:00'  # New delivery time
        }
        response = self.client.patch(update_url, redelivery_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'redelivery_assigned')
        self.assertEqual(len(response.data['drivers']), 1)
        self.assertEqual(response.data['drivers'][0], self.driver2.id)

        # Update to redelivery in progress
        in_progress_data = {'status': 'redelivery_in_progress'}
        response = self.client.patch(update_url, in_progress_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'redelivery_in_progress')

        # Complete redelivery
        complete_data = {'status': 'redelivery_complete'}
        response = self.client.patch(update_url, complete_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'redelivery_complete')

        # Verify history contains all status changes
        assignment = Assignment.objects.get(id=assignment_id)
        self.assertEqual(len(assignment.previous_assignments), 5)  # Should have 5 history entries
        
        # Verify the sequence of status changes in history
        status_sequence = [entry['status'] for entry in assignment.previous_assignments]
        expected_sequence = [
            'order_placed',
            'misdelivery',
            'redelivery_assigned',
            'redelivery_in_progress',
            'redelivery_complete'
        ]
        self.assertEqual(status_sequence, expected_sequence)

        # Verify the driver change in history
        initial_driver_history = assignment.previous_assignments[0]['drivers']
        redelivery_driver_history = assignment.previous_assignments[2]['drivers']  # Check drivers at redelivery_assigned stage
        self.assertEqual(initial_driver_history, [self.user.id])
        self.assertEqual(redelivery_driver_history, [self.driver2.id])





"""from decimal import Decimal
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse

from products.models import Product
from orders.models import Order, OrderItem
from stores.models import Store

class OrderViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create test store
        self.store = Store.objects.create(name="Test Store")

        # Create test products
        self.product1 = Product.objects.create(name="Test Product 1", price=10.99, quantity=2)
        self.product2 = Product.objects.create(name="Test Product 2", price=20.99, quantity=3)

        # Sample order data
        self.valid_order_data = {
            "store": self.store.id,
            "first_name": "John",
            "last_name": "Doe",
            "phone_num": "+1234567890",
            "address": "123 Test St",
            "customer_email": "test@example.com",
            "customer_num": "CUST001",
            "preferred_delivery_time": "14:00:00",
            "delivery_instructions": "Leave at door",
            "notes": "Test order",
            "invoice_num": "1234",
            "items": [
                {"product_name_input": self.product1.name, "product_name":self.product1.name, "quantity": 2, "price_at_order":self.product1.price},
                {"product_name_input": self.product2.name, "product_name":self.product2.name, "quantity": 3, "price_at_order":self.product2.price}
            ]
            }

    def test_update_order_success(self):
    
    #Test updating an existing order

        # **Step 1: Create an Order**
        response = self.client.post(
            reverse('order-list'),
            self.valid_order_data,
            format='json'
        )


        # Check order was created successfully
        print("CREATE RESPONSE:", response.data)  # Debugging line
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order_id = response.data['id']

        # **Step 2: Prepare Update Data**
        updated_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "items": [
                {"product_name_input": self.product1.name, "product_name": self.product1.id, "quantity": 5, "price_at_order":self.product1.price},
                {"product_name_input": self.product2.name, "product_name": self.product2.id, "quantity": 1, "price_at_order":self.product1.price}
            ]
        }

        # **Step 3: Send PATCH Request**
        update_response = self.client.patch(
            reverse('order-detail', args=[order_id]),
            updated_data,
            format='json'
        )

        print("UPDATE RESPONSE:", update_response.data)  # Debugging line
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        # **Step 4: Verify Changes in the Database**
        updated_order = Order.objects.get(id=order_id)
        self.assertEqual(updated_order.first_name, "Jane")
        self.assertEqual(updated_order.last_name, "Smith")

        # Fetch updated items
        updated_item1 = OrderItem.objects.get(order=updated_order, product=self.product1)
        updated_item2 = OrderItem.objects.get(order=updated_order, product=self.product2)

        # Check if quantities are updated correctly
        self.assertEqual(updated_item1.quantity, 5)  # Should be updated to 5
        self.assertEqual(updated_item2.quantity, 1)  # Should be updated to 1

"""


"""import os
from django.conf import settings
from django.test import TestCase, Client
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile

class ProductImportViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = "/api/import-products/"  # Adjust if your URL is different

    def test_upload_valid_xml_file(self):
        valid_xml_content = <?xml version="1.0" encoding="UTF-8"?>
<products xmlns:g="http://base.google.com/ns/1.0">
    <item>
        <g:id>123</g:id>
        <title>Test Product</title>
        <description>Sample description</description>
        <g:price>10.99</g:price>
    </item>
</products>.encode("utf-8")
        
        xml_file = SimpleUploadedFile("test.xml", valid_xml_content, content_type="application/xml")
        response = self.client.post(self.url, {"file": xml_file}, format="multipart")
        
        # Expect a success response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("success", response.json())

    def test_upload_missing_file(self):
        response = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())

    def test_upload_invalid_file_type(self):
        txt_file = SimpleUploadedFile("test.txt", b"Invalid file content", content_type="text/plain")
        response = self.client.post(self.url, {"file": txt_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())

    def test_upload_invalid_xml_content(self):
        invalid_xml_file = SimpleUploadedFile("invalid.xml", b"<products><item></invalid>", content_type="application/xml")
        response = self.client.post(self.url, {"file": invalid_xml_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("message", response.json())
"""

"""from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import override_settings
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.core import mail
from django.conf import settings
from accounts.models import User
from stores.models import Store


from django.contrib.auth.tokens import default_token_generator

class UserCreationTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # Create manager user
        self.manager = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='password123',
            is_manager=True,
            is_active=True,
            is_email_verified=True
        )
        # Create store
        from stores.models import Store  # Add import
        self.store = Store.objects.create(name='Test Store')
        self.manager.stores.add(self.store)

    def test_manager_login(self):
        response = self.client.post('/api/login/', {
            'username': 'manager',  # Changed from email to username
            'password': 'password123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_create_user_with_token(self):

        # Admin user setup
        self.admin_user = User.objects.create(
            username='ADMIN',
            email='ADMIN@ADMIN.com',    
            is_manager=True,
            is_driver=True
        )
        self.user_data = {
            'username': 'Abright',
            'email': 'landryabright@google.com',
            'password': 'password',
            'first_name': 'Landry',
            'last_name': 'Abright',
            'is_driver':'True',
            'stores': [self.store.id]
        }

        # Then proceed with login and test
        login_response = self.client.post('/api/login/', {
            'username': 'manager',
            'password': 'password123'
        })
        token = login_response.data['access']
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post('/api/users/', self.user_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
"""

"""
User = get_user_model()

class PasswordResetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpassword123'
        )

    def test_request_password_reset(self):
        
        #Test requesting a password reset
        
        response = self.client.post('/api/users/request_password_reset/', {
            'email': self.user.email
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh user from database
        updated_user = User.objects.get(id=self.user.id)
        
        # Check reset token was generated
        self.assertIsNotNone(updated_user.password_reset_token)
        self.assertIsNotNone(updated_user.password_reset_token_created_at)

    def test_request_password_reset_nonexistent_email(self):
        
        #Test requesting reset for non-existent email
        
        response = self.client.post('/api/users/request_password_reset/', {
            'email': 'nonexistent@example.com'
        })
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reset_password_success(self):
        
        #Test successful password reset
        
        # Generate reset token
        self.user.password_reset_token = 'valid_reset_token'
        self.user.password_reset_token_created_at = timezone.now()
        self.user.save()

        response = self.client.post('/api/users/reset_password/', {
            'token': 'valid_reset_token',
            'new_password': 'newpassword123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        updated_user = User.objects.get(id=self.user.id)
        self.assertTrue(updated_user.check_password('newpassword123'))
        
        # Verify reset token was cleared
        self.assertIsNone(updated_user.password_reset_token)
        self.assertIsNone(updated_user.password_reset_token_created_at)

    def test_reset_password_invalid_token(self):
        
        #Test reset with invalid token
        
        response = self.client.post('/api/users/reset_password/', {
            'token': 'invalid_token',
            'new_password': 'newpassword123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_expired_token(self):
        
        #Test reset with expired token
        
        # Set token creation time to more than 1 hour ago
        old_time = timezone.now() - timezone.timedelta(hours=2)
        self.user.password_reset_token = 'expired_token'
        self.user.password_reset_token_created_at = old_time
        self.user.save()

        response = self.client.post('/api/users/reset_password/', {
            'token': 'expired_token',
            'new_password': 'newpassword123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_weak_password(self):
        
        #Test reset with weak password
        
        # Generate reset token
        self.user.password_reset_token = 'valid_reset_token'
        self.user.password_reset_token_created_at = timezone.now()
        self.user.save()

        response = self.client.post('/api/users/reset_password/', {
            'token': 'valid_reset_token',
            'new_password': '123'  # Too short
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_reset_email(self):
        
        #Test email sending for password reset
        
        # Clear outbox
        mail.outbox = []

        # generate token
        reset_token = default_token_generator.make_token(self.user)

        # Send reset email
        from api.accounts.utils import send_reset_email  # Adjust import
        result = send_reset_email(self.user, reset_token)

        # Check email was sent
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        # Check email details
        email = mail.outbox[0]
        self.assertEqual(email.subject, f'Password Reset for {settings.SITE_NAME}')
        self.assertIn(self.user.email, email.to)

"""
"""
# tests.py
from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from accounts.models import User
from stores.models import Store

from django.contrib.auth import get_user_model

import project.settings


class UserProfileUpdateTest(APITestCase):
    def setUp(self):
        # Store setup
        self.mckinney = Store.objects.create(
            name='mckinney',
            address='123 north',
            phone='1234567890'
        )
        self.celina = Store.objects.create(
            name='celina',
            address='123 main',
            phone='1234567890'
        )

        # User setup
        self.user_data = {
            'username': 'Abright',
            'email': 'landryabright@google.com',
            'password': 'password123',
            'first_name': 'Landry',
            'last_name': 'Abright',
            'is_driver': True,
            'stores': [self.mckinney.id, self.celina.id]
        }
        
        # Create user
        self.user = User.objects.create_user(**{k:v for k,v in self.user_data.items() if k != 'stores'})
        
        # Setup client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_update_profile_success(self):
        
        #Test successful profile update
        
        update_data = {
            'first_name': 'LandryUpdated',
            'last_name': 'AbrightUpdated'
        }
        
        response = self.client.patch(
            f'/api/users/{self.user.id}/update_profile/', 
            update_data, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh user from database
        updated_user = User.objects.get(id=self.user.id)
        self.assertEqual(updated_user.first_name, 'LandryUpdated')
        self.assertEqual(updated_user.last_name, 'AbrightUpdated')

    def test_update_profile_forbidden(self):
        
        #Test updating another user's profile
        
        # Create another user
        other_user = User.objects.create_user(
            username='OtherUser',
            email='other@example.com',
            password='password123'
        )
        
        update_data = {
            'first_name': 'Hacked'
        }
        
        response = self.client.patch(
            f'/api/users/{other_user.id}/update_profile/', 
            update_data, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_profile_invalid_data(self):
        
        #Test updating profile with invalid data
        
        # Assuming email must be unique
        update_data = {
            'email': 'invalid@email'  # potentially invalid email
        }
        
        response = self.client.patch(
            f'/api/users/{self.user.id}/update_profile/', 
            update_data, 
            format='json'
        )
        
        # Validate the response based on your validation logic
        # This might be status.HTTP_400_BAD_REQUEST if email is invalid
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])

    def test_update_profile_unauthenticated(self):
        
        #Test profile update without authentication
        
        # Logout the user
        self.client.logout()
        
        update_data = {
            'first_name': 'Unauthorized'
        }
        
        response = self.client.patch(
            f'/api/users/{self.user.id}/update_profile/', 
            update_data, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
"""
"""
class EmailVerificationTest(APITestCase):
    def setUp(self):
        # Store setup
        self.mckinney = Store.objects.create(
            name='mckinney',
            address='123 north',
            phone='1234567890'
        )
        self.celina = Store.objects.create(
            name='celina',
            address='123 main',
            phone='1234567890'
        )

        # Admin user setup
        self.admin_user = User.objects.create(
            username='ADMIN',
            email='ADMIN@ADMIN.com',    
            is_manager=True,
            is_driver=True
        )

        self.user_data = {
            'username': 'Abright',
            'email': 'landryabright@google.com',
            'password': 'password',
            'first_name': 'Landry',
            'last_name': 'Abright',
            'is_driver':'True',
            'stores': [self.mckinney.id, self.celina.id]
        }

   
    def test_login_workflow(self):
        # Register user
        response = self.client.post('/api/users/', self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify email
        user = User.objects.get(email=self.user_data['email'])
        verify_url = f'/api/users/verify_email/?token={user.email_verification_token}'
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Login
        login_data = {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        }
        response = self.client.post('/api/login/', login_data)
        print(f"\nLogin attempt to: /api/login/")
        print(f"Status: {response.status_code}")
        print(f"Content: {response.content}")
        print(response.status_code)
        print(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify tokens received
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Logout
        logout_data = {'refresh': response.data['refresh']}
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        response = self.client.post('/api/logout/', logout_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
"""
        
"""
    def test_manual_email_verification(self):
        # Create user and get token
        response = self.client.post('/api/users/', self.user_data, format='json')
        user = User.objects.get(email=self.user_data['email'])
        user.refresh_from_db()

        users = User.objects.all()
        for u in users:
            print(f"User: {u.email}, Token: {u.email_verification_token}")
        
        print("\n=== Manual Verification Steps ===")
        print("1. Start Django server")
        print("2. Visit this URL:")
        print(f"http://localhost:8000/api/users/verify_email/?token={user.email_verification_token}")
        print("3. Press Enter after visiting URL")
        
        input("\nPress Enter after verification...")
        
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified, "Email verification failed")
"""
"""
    def test_email_verification_endpoint(self):
        # Create user and get token
        response = self.client.post('/api/users/', self.user_data, format='json')
        user = User.objects.get(email=self.user_data['email'])
        token = user.email_verification_token

        # Test verification endpoint
        verify_url = f'/api/users/verify_email/?token={token}'
        response = self.client.get(verify_url)
        
        # Verify response and user state
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        print(user.is_email_verified)

        # Test invalid token
        response = self.client.get('/api/users/verify_email/?token=invalid')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
"""
"""
    def test_manual_email_verification(self):
        # Create user
        response = self.client.post('/api/users/', self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Get the user
        user = User.objects.get(email=self.user_data['email'])
        print(f'user: {user}')
        # Verify initial state
        self.assertFalse(user.is_email_verified)

        send_verification_email(user)
        # print all

        users = User.objects.all()
        for u in users:
            print(f'username: {u.first_name}')
            print(u.email_verification_token)
            print(u.email)

        
        # Print verification URL for manual testing
        print("\n=== MANUAL VERIFICATION REQUIRED ===")
        print(f"1. Start your Django server")
        print(f"2. Visit this URL in your browser:")
        print(f"http://localhost:8000/api/users/verify_email/?token={user.email_verification_token}")
        print("3. After visiting the URL, press Enter to continue the test...")
        
        input("\nPress Enter after you've completed the verification...")
        
        # Refresh user from database to get updated state
        user.refresh_from_db()
        
        # Verify the email was verified
        self.assertTrue(user.is_email_verified, "Email verification failed - user.email_verified is still False")
"""

"""
class EmailVerificationTest(APITestCase):
    def setUp(self):

        # First, we create a pretend store called 'mckinney'
        self.mckinney = Store.objects.create(
            name='mckinney',
            address='123 north',
            phone='1234567890'
        )
        self.celina = Store.objects.create(
            name='celina',
            address='123 main',
            phone='1234567890'
        )

        # Then we create a test user who has special permissions to send POST and GET
        self.test_user = User.objects.create(
            username='testuser',
            email='test@test.com',
            is_manager=True,
            is_driver=True
        )

        # We give this test user permission to use our API
        self.client = APIClient()
        self.client.force_authenticate(user=self.test_user)

        self.user_data = {
            'username': 'Abright',
            'email': 'landryabright@google.com',
            'password': 'password',
            'password2': 'password',
            'first_name': 'Test',
            'last_name': 'User',
            'is_driver':'True',
            'stores': [self.mckinney.id, self.celina.id]  # Connect user to our store
        }

    def test_email_verification_flow(self):
        # Debug: Print all available URLs
        from django.urls import get_resolver
        print("\nAvailable URL patterns:")
        for pattern in get_resolver().url_patterns:
            if hasattr(pattern, 'url_patterns'):
                for url in pattern.url_patterns:
                    print(f"  {url.pattern}")
        
        # Rest of your test code...
        response = self.client.post('/api/users/', self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        user = User.objects.get(email=self.user_data['email'])
        token = user.email_verification_token
        
        verification_url = f'/api/users/verify_email/?token={token}'  # Use trailing slash
        print(f"\nAttempting verification with URL: {verification_url}")
        
        response = self.client.get(verification_url)
        print(f"Response status: {response.status_code}")
        print(f"Response content: {getattr(response, 'data', response.content)}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)



        # Print available URLs for debugging
        #from django.urls import get_resolver
        #url_patterns = get_resolver().url_patterns
        #print("Available URL patterns:")
        #for pattern in url_patterns:
        #    print(f"  - {pattern.pattern}")
        
        #response = self.client.get(verification_url, follow=True)
        #print("Verification response:", response.status_code, getattr(response, 'data', response.content))
        #self.assertEqual(response.status_code, status.HTTP_200_OK)

    #def test_invalid_verification_token(self):
    #    # Test with invalid token
    #    response = self.client.get('/api/users/verify-email/?token=invalid-token')
    #    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

"""
"""
class UserTests(APITestCase):
    def setUp(self):
        # First, we create a pretend store called 'mckinney'
        self.mckinney = Store.objects.create(
            name='mckinney',
            address='123 north',
            phone='1234567890'
        )
        self.celina = Store.objects.create(
            name='celina',
            address='123 main',
            phone='1234567890'
        )

        # Then we create a test user who has special permissions to send POST and GET
        self.test_user = User.objects.create(
            username='testuser',
            email='test@test.com',
            is_manager=True,
            is_driver=True
        )

        # We give this test user permission to use our API
        self.client = APIClient()
        self.client.force_authenticate(user=self.test_user)

    def test_create_user_with_stores(self):
        # We make a dictionary with information for our new user
        user_data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'newpass123',
            'is_manager': False,
            'is_driver': True,
            'stores': [self.mckinney.id, self.celina.id]  # Connect user to our store
        }

        # We try to create this new user through our API
        response = self.client.post('/api/users/', user_data, format='json')
        
        # We check if everything worked correctly:
        
        # 1. Did we get a "success" response? (201 means "created successfully")
        self.assertEqual(response.status_code, 201)
        
        # 2. Did it save the right username?
        #self.assertEqual(response.data['username'], 'newuser')
        
        # 3. Did it save the right email?
        #self.assertEqual(response.data['email'], 'newuser@test.com')
        
        # 4. Did it mark them as a driver?
        #self.assertEqual(response.data['is_driver'], True)
        
        # 5. Did it connect them to our store?
        #self.assertIn(self.mckinney.id, response.data['stores'])
        #self.assertIn(self.celina.id, response.data['stores'])

        # 6. Finally, we check if we can find this user in our database
        created_user = User.objects.get(username='newuser')
        #self.assertTrue(created_user.stores.filter(id=self.mckinney.id).exists())

        # We try the helper method get all stores
        response = self.client.get(f'/api/users/{created_user.id}/stores/')

        # 1. Did we get a "success" response? (201 means "created successfully")
        self.assertEqual(response.status_code, 200)
        #self.assertIn(self.mckinney.id, [store['id'] for store in response.data])
        #self.assertIn(self.celina.id, [store['id'] for store in response.data])
       
        print(self.mckinney.id)
        # We try the helper method get all stores
        response = self.client.get(f'/api/stores/{self.mckinney.id}/users/')
        print(response)

        print(response.data)
    
        # 1. Did we get a "success" response? (201 means "created successfully")
        self.assertEqual(response.status_code, 200)
"""