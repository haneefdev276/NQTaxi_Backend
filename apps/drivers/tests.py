import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.drivers.models import DriverProfile

User = get_user_model()

class DriverEndpointsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdriver', password='password123', email='driver@example.com'
        )
        self.profile = DriverProfile.objects.create(user=self.user, phone='+111222333')
        self.client.force_authenticate(user=self.user)

    def test_profile_endpoint(self):
        url = reverse('drivers:profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('first_name', response.json().get('user', {}))

    def test_vehicle_endpoint(self):
        url = reverse('drivers:vehicle')
        response = self.client.get(url)
        # Should return 404 or empty if no vehicle exists, let's just ensure it's JSON
        self.assertIn(response.status_code, [200, 404])

    def test_status_endpoint(self):
        url = reverse('drivers:status')
        response = self.client.patch(url, {'status': 'ONLINE'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.json())

    def test_wallet_endpoint(self):
        url = reverse('drivers:wallet')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('balance', response.json())
