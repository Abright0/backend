import uuid
from rest_framework.test import APITestCase, APIClient
from django.utils.timezone import now
from datetime import date, time

from accounts.models import User
from products.models import Product
from stores.models import Store
from orders.models import Order
from assignments.models import DeliveryAttempt, ScheduledItem


class AssignmentTests(APITestCase):
    def setUp(self):
        # Generate unique emails
        admin_email = f"admin_{uuid.uuid4().hex[:6]}@test.com"
        driver1_email = f"driver1_{uuid.uuid4().hex[:6]}@test.com"
        driver2_email = f"driver2_{uuid.uuid4().hex[:6]}@test.com"

        # Create store
        self.store = Store.objects.create(name="Test Store", address="123 Main St", phone="555-555-5555")

        # Create admin and drivers
        self.admin_user = User.objects.create_user(username='ADMIN', email=admin_email, password='adminpass123', is_manager=True, is_driver=True)
        self.admin_user.stores.add(self.store)

        self.user = User.objects.create_user(username='driver1', email=driver1_email, password='password123', is_driver=True)
        self.user.stores.add(self.store)

        self.driver2 = User.objects.create_user(username='driver2', email=driver2_email, password='password123', is_driver=True)
        self.driver2.stores.add(self.store)

        # Create products
        self.product1 = Product.objects.create(name="Test Product 1", price=10.99, quantity=5)
        self.product2 = Product.objects.create(name="Test Product 2", price=20.99, quantity=10)

        # Authenticated client
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

        self.create_order_for_test()

    def create_order_for_test(self):
        url = '/api/orders/'
        data = {
            "store": self.store.id,
            "first_name": "John",
            "last_name": "Doe",
            "phone_num": "+1234567890",
            "address": "123 Test St",
            "customer_email": "john.doe@test.com",
            "customer_num": "CUST001",
            "preferred_delivery_time": "14:00:00",
            "delivery_instructions": "Leave at door",
            "notes": "Test order",
            "invoice_num": "INV-1234",
            "items": [
                {"product_name_input": self.product1.name, "quantity": 1, "price_at_order": self.product1.price},
                {"product_name_input": self.product2.name, "quantity": 2, "price_at_order": self.product2.price}
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)

        self.order = Order.objects.get(id=response.data['id'])
        self.item1 = self.order.items.get(product_name_input=self.product1.name)
        self.item2 = self.order.items.get(product_name_input=self.product2.name)
        self.driver_a = self.user
        self.driver_b = self.driver2

    def test_delivery_with_scheduled_items_only(self):
        attempt = DeliveryAttempt.objects.create(
            order=self.order,
            status='complete',
            delivery_date=date.today(),
            delivery_time=time(9, 0),
            result='Initial delivery with partial success'
        )
        attempt.drivers.add(self.driver_a)

        redelivery = DeliveryAttempt.objects.create(
            order=self.order,
            status='order_placed',
            delivery_date=date.today(),
            delivery_time=time(15, 0),
            result='Scheduled redelivery'
        )
        redelivery.drivers.add(self.driver_b)

        scheduled = ScheduledItem.objects.create(
            delivery_attempt=redelivery,
            order_item=self.item2,
            quantity=1
        )

        self.assertEqual(scheduled.delivery_attempt, redelivery)
        self.assertEqual(scheduled.order_item, self.item2)
        self.assertEqual(scheduled.quantity, 1)

    def test_delivery_with_scheduled_items(self):
        initial = DeliveryAttempt.objects.create(
            order=self.order,
            status='complete',
            delivery_date=now().date(),
            delivery_time=time(10, 0),
            result='Delivered partially'
        )
        initial.drivers.add(self.driver_a)

        redelivery = DeliveryAttempt.objects.create(
            order=self.order,
            status='order_placed',
            delivery_date=now().date(),
            delivery_time=time(15, 0),
            result='Follow-up delivery'
        )
        redelivery.drivers.add(self.driver_b)

        scheduled = ScheduledItem.objects.create(
            delivery_attempt=redelivery,
            order_item=self.item2,
            quantity=1
        )

        self.assertEqual(redelivery.scheduled_items.count(), 1)
        self.assertEqual(scheduled.quantity, 1)

    def test_delivery_attempt_model_fields(self):
        attempt = DeliveryAttempt.objects.create(
            order=self.order,
            status='en_route',
            delivery_date=date.today(),
            delivery_time=time(13, 0),
            result='On the way'
        )
        attempt.drivers.add(self.driver_a, self.driver_b)

        self.assertEqual(attempt.order, self.order)
        self.assertEqual(attempt.status, 'en_route')
        self.assertEqual(attempt.result, 'On the way')
        self.assertIn(self.driver_a, attempt.drivers.all())
        self.assertIn(self.driver_b, attempt.drivers.all())
        self.assertEqual(attempt.delivery_date, date.today())
        self.assertEqual(attempt.delivery_time, time(13, 0))
        self.assertIsNotNone(attempt.created_at)

    def test_scheduled_item_model_fields(self):
        attempt = DeliveryAttempt.objects.create(
            order=self.order,
            status='order_placed',
            delivery_date=date.today(),
            delivery_time=time(11, 0),
            result='Scheduled'
        )
        item = ScheduledItem.objects.create(
            delivery_attempt=attempt,
            order_item=self.item1,
            quantity=1
        )

        self.assertEqual(item.delivery_attempt, attempt)
        self.assertEqual(item.order_item, self.item1)
        self.assertEqual(item.quantity, 1)
