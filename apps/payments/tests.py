from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.customers.models import RiderProfile

User = get_user_model()

class PaymentEndpointsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testpayment', password='password123', email='payment@example.com'
        )
        self.profile = RiderProfile.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)

    def test_transaction_history_endpoint(self):
        url = reverse('transaction-history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return a list or dict with history
        self.assertTrue(isinstance(response.json(), (list, dict)))
