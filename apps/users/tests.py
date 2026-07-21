from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.users.models import CustomerProfile
from apps.drivers.models import DriverProfile

User = get_user_model()

class UserRegistrationTests(APITestCase):
    def test_register_customer(self):
        url = reverse('users:register_customer')
        data = {
            'username': 'newcustomer',
            'password': 'StrongPassword123!',
            'email': 'customer@example.com',
            'first_name': 'Test',
            'last_name': 'Customer',
            'phone': '+1234567890'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'newcustomer')
        self.assertEqual(response.data['email'], 'customer@example.com')
        self.assertTrue(User.objects.filter(username='newcustomer').exists())
        self.assertTrue(CustomerProfile.objects.filter(user__username='newcustomer').exists())

    def test_register_driver(self):
        url = reverse('users:register_driver')
        data = {
            'username': 'newdriver',
            'password': 'StrongPassword123!',
            'email': 'driver@example.com',
            'first_name': 'Test',
            'last_name': 'Driver',
            'phone': '+0987654321'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'newdriver')
        self.assertEqual(response.data['email'], 'driver@example.com')
        self.assertTrue(User.objects.filter(username='newdriver').exists())
        self.assertTrue(DriverProfile.objects.filter(user__username='newdriver').exists())
