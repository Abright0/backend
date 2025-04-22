from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

class EmailReceiveTest(APITestCase):
    def test_receive_email_endpoint(self):
        url = reverse('receive-email')
        data = {
            "sender": "sender@example.com",
            "subject": "Unit Test Email",
            "body": "This is the body of the test email.",
            "message_id": "test12345"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], "Email data received successfully.")
