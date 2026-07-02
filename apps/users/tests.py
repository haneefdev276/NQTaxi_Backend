import uuid

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from django.urls import resolve, reverse
from rest_framework.test import APITestCase

from apps.users.views import RegisterView

User = get_user_model()


class AuthUrlTests(SimpleTestCase):
    def test_register_endpoint_is_available_at_legacy_and_v1_prefixes(self):
        legacy_match = resolve('/auth/register/')
        v1_match = resolve('/api/v1/auth/register/')

        self.assertEqual(legacy_match.func.view_class, RegisterView)
        self.assertEqual(v1_match.func.view_class, RegisterView)


class RegisterViewTests(APITestCase):
    def test_register_returns_success_payload_with_tokens(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'testuser01',
                'email': 'testuser01@example.com',
                'password': 'StrongPass123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])
        self.assertEqual(response.json()['message'], 'User registered successfully')
        self.assertEqual(response.json()['user']['username'], 'testuser01')
        self.assertIsInstance(response.json()['user']['id'], str)
        self.assertEqual(str(uuid.UUID(response.json()['user']['id'])), response.json()['user']['id'])
        self.assertIn('access', response.json()['tokens'])
        self.assertIn('refresh', response.json()['tokens'])

    def test_login_returns_success_payload_with_tokens(self):
        User.objects.create_user(
            username='loginuser',
            email='loginuser@example.com',
            password='StrongPass123!',
        )

        response = self.client.post(
            reverse('token_obtain_pair'),
            {
                'username': 'loginuser',
                'password': 'StrongPass123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])
        self.assertEqual(response.json()['message'], 'Login successful')
        self.assertEqual(response.json()['user']['username'], 'loginuser')
        self.assertIsInstance(response.json()['user']['id'], str)
        self.assertEqual(str(uuid.UUID(response.json()['user']['id'])), response.json()['user']['id'])
        self.assertIn('access', response.json()['tokens'])
        self.assertIn('refresh', response.json()['tokens'])

    def test_login_creates_rider_profile_if_missing(self):
        from apps.customers.models import RiderProfile

        User.objects.create_user(
            username='loginprofileuser',
            email='loginprofile@example.com',
            password='StrongPass123!',
        )

        self.assertFalse(RiderProfile.objects.filter(user__username='loginprofileuser').exists())

        response = self.client.post(
            reverse('token_obtain_pair'),
            {
                'username': 'loginprofileuser',
                'password': 'StrongPass123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(RiderProfile.objects.filter(user__username='loginprofileuser').exists())

    def test_login_invalid_credentials_returns_errors_payload(self):
        response = self.client.post(
            reverse('token_obtain_pair'),
            {
                'username': 'missinguser',
                'password': 'WrongPass123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('errors', data)

    def test_token_refresh_returns_success_payload_with_tokens(self):
        User.objects.create_user(
            username='refreshuser',
            email='refreshuser@example.com',
            password='StrongPass123!',
        )

        login_response = self.client.post(
            reverse('token_obtain_pair'),
            {
                'username': 'refreshuser',
                'password': 'StrongPass123!',
            },
            format='json',
        )
        refresh_token = login_response.json()['tokens']['refresh']

        response = self.client.post(
            reverse('token_refresh'),
            {'refresh': refresh_token},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(response.json()['message'], 'Token refreshed successfully')
        self.assertIn('access', response.json()['tokens'])
        self.assertEqual(response.json()['tokens']['refresh'], refresh_token)
