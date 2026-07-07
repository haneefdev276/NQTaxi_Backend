from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.customers.models import RiderProfile, SavedPlace
from apps.ratings.models import Rating
from apps.trips.models import Trip

User = get_user_model()


class SavedPlaceDeleteTests(APITestCase):
    def test_delete_returns_json_confirmation(self):
        user = User.objects.create_user(username='savedplaceuser', email='savedplace@example.com', password='StrongPass123!')
        rider_profile = RiderProfile.objects.get_or_create(user=user)[0]
        saved_place = SavedPlace.objects.create(
            rider=rider_profile,
            label='home',
            name='Home',
            address='Some address',
            latitude='12.34567890',
            longitude='76.54321098',
        )

        self.client.force_authenticate(user=user)
        response = self.client.delete(f'/customers/saved-places/{saved_place.pk}/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(response.json()['message'], 'Saved place deleted successfully')
        self.assertEqual(response.json()['deleted_id'], str(saved_place.pk))
        self.assertFalse(SavedPlace.objects.filter(pk=saved_place.pk).exists())


class SavedPlaceCreateTests(APITestCase):
    def test_create_custom_label_returns_success_payload(self):
        user = User.objects.create_user(
            username='savedplaceuser',
            email='savedplace@example.com',
            password='StrongPass123!',
        )
        RiderProfile.objects.get_or_create(user=user)

        self.client.force_authenticate(user=user)
        response = self.client.post(
            '/customers/saved-places/',
            {
                'label': 'Gym',
                'name': 'Fitness Center',
                'address': 'MG Road, Bengaluru',
                'latitude': '12.971598',
                'longitude': '77.641267',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Saved place added successfully')
        self.assertEqual(data['saved_place']['label'], 'gym')

    def test_create_allows_multiple_custom_labels(self):
        user = User.objects.create_user(
            username='savedplaceuser2',
            email='savedplace2@example.com',
            password='StrongPass123!',
        )
        RiderProfile.objects.get_or_create(user=user)

        self.client.force_authenticate(user=user)
        for label in ('gym', 'school'):
            response = self.client.post(
                '/customers/saved-places/',
                {
                    'label': label,
                    'name': label.title(),
                    'address': 'Bengaluru',
                    'latitude': '12.971598',
                    'longitude': '77.641267',
                },
                format='json',
            )
            self.assertEqual(response.status_code, 201, response.json())

        list_response = self.client.get('/customers/saved-places/')
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()['saved_places']), 2)

    def test_home_label_must_be_unique(self):
        user = User.objects.create_user(
            username='savedplaceuser3',
            email='savedplace3@example.com',
            password='StrongPass123!',
        )
        rider_profile = RiderProfile.objects.get_or_create(user=user)[0]
        SavedPlace.objects.create(
            rider=rider_profile,
            label='home',
            address='Home address',
            latitude='12.971598',
            longitude='77.641267',
        )

        self.client.force_authenticate(user=user)
        response = self.client.post(
            '/customers/saved-places/',
            {
                'label': 'home',
                'address': 'Another home',
                'latitude': '12.971598',
                'longitude': '77.641267',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertIn('label', response.json()['errors'])


class RatingsAndPaymentMethodTests(APITestCase):
    def test_ratings_endpoint_returns_summary_and_paginated_results(self):
        user = User.objects.create_user(username='rider1', email='rider1@example.com', password='StrongPass123!')
        rider_profile = RiderProfile.objects.get_or_create(user=user)[0]
        driver = User.objects.create_user(username='driver1', email='driver1@example.com', password='StrongPass123!')

        trip = Trip.objects.create(
            rider=user,
            driver=driver,
            pickup_address='Outer Ring Road, Bengaluru',
            pickup_latitude='12.934533',
            pickup_longitude='77.695814',
            drop_address='Indiranagar, Bengaluru',
            drop_latitude='12.971598',
            drop_longitude='77.641267',
            status=Trip.Status.COMPLETED,
            fare='182.50',
            distance_km='8.40',
            requested_at=timezone.now().replace(hour=10, minute=0, second=0, microsecond=0),
            completed_at=timezone.now().replace(hour=10, minute=25, second=0, microsecond=0),
        )

        Rating.objects.create(trip=trip, given_by_rider=user, score=Decimal('4.5'), comment='Great ride')
        Rating.objects.create(trip=trip, given_by_rider=driver, score=Decimal('5.0'), comment='Excellent')
        Rating.objects.create(trip=trip, given_by_rider=driver, score=Decimal('3.5'), comment='Fine')

        self.client.force_authenticate(user=user)
        response = self.client.get('/customers/ratings/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Ratings retrieved successfully')
        self.assertEqual(data['summary']['total_given'], 1)
        self.assertEqual(data['summary']['average_rating_given'], 4.5)
        self.assertEqual(data['summary']['total_received'], 2)
        self.assertEqual(data['summary']['average_rating_received'], 4.2)
        self.assertEqual(data['given']['count'], 1)
        self.assertEqual(data['received']['count'], 2)
        self.assertEqual(data['given']['ratings'][0]['given_by'], 'rider1')
        self.assertEqual(data['received']['ratings'][0]['given_by'], 'driver1')

    def test_trip_history_returns_success_payload(self):
        user = User.objects.create_user(username='tripuser', email='tripuser@example.com', password='StrongPass123!')
        driver = User.objects.create_user(username='tripdriver', email='tripdriver@example.com', password='StrongPass123!')

        Trip.objects.create(
            rider=user,
            driver=driver,
            pickup_address='Outer Ring Road, Bengaluru',
            pickup_latitude='12.934533',
            pickup_longitude='77.695814',
            drop_address='Indiranagar, Bengaluru',
            drop_latitude='12.971598',
            drop_longitude='77.641267',
            status=Trip.Status.COMPLETED,
            fare='182.50',
            distance_km='8.40',
            requested_at=timezone.now().replace(hour=10, minute=0, second=0, microsecond=0),
            completed_at=timezone.now().replace(hour=10, minute=25, second=0, microsecond=0),
        )

        self.client.force_authenticate(user=user)
        response = self.client.get('/customers/trip-history/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Trip history retrieved successfully')
        self.assertEqual(len(data['trips']), 1)
        self.assertEqual(data['trips'][0]['status'], 'completed')
        self.assertEqual(data['trips'][0]['driver_name'], 'tripdriver')
        self.assertLessEqual(data['trips'][0]['requested_at'], data['trips'][0]['completed_at'])
        self.assertIsNone(data['trips'][0]['started_at'])

    def test_saved_places_work_without_existing_rider_profile(self):
        user = User.objects.create_user(
            username='noprofileuser',
            email='noprofile@example.com',
            password='StrongPass123!',
        )

        self.client.force_authenticate(user=user)
        response = self.client.get('/customers/saved-places/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(response.json()['saved_places'], [])

    def test_wallet_returns_pagination_metadata(self):
        user = User.objects.create_user(
            username='walletuser',
            email='wallet@example.com',
            password='StrongPass123!',
        )
        rider_profile = RiderProfile.objects.get_or_create(user=user)[0]
        from apps.customers.models import WalletTransaction

        for index in range(11):
            WalletTransaction.objects.create(
                rider=rider_profile,
                type=WalletTransaction.TransactionType.CREDIT,
                amount=10000,
                description=f'Top-up {index}',
                status=WalletTransaction.Status.COMPLETED,
            )

        self.client.force_authenticate(user=user)
        response = self.client.get('/customers/wallet/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Wallet retrieved successfully')
        self.assertEqual(data['count'], 11)
        self.assertEqual(len(data['transactions']), 10)
        self.assertIsNotNone(data['next'])

    def test_payment_method_rejects_raw_card_details(self):
        user = User.objects.create_user(username='paymentuser', email='paymentuser@example.com', password='StrongPass123!')
        RiderProfile.objects.get_or_create(user=user)[0]

        self.client.force_authenticate(user=user)
        response = self.client.post('/customers/payment-methods/', {
            'type': 'card',
            'card_number': '4242424242424242',
            'cvv': '123',
            'card_last4': '4242',
            'card_expiry': '12/28',
            'card_holder': 'Test Rider',
            'is_default': True,
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertIn('Raw card details are not accepted', response.json()['errors']['non_field_errors'][0])

    def test_payment_method_create_returns_success_payload(self):
        user = User.objects.create_user(
            username='paymentcreateuser',
            email='paymentcreate@example.com',
            password='StrongPass123!',
        )
        RiderProfile.objects.get_or_create(user=user)

        self.client.force_authenticate(user=user)
        response = self.client.post(
            '/customers/payment-methods/',
            {
                'type': 'card',
                'card_last4': '4242',
                'card_brand': 'Visa',
                'card_expiry': '12/28',
                'card_holder': 'Bal Reddy',
                'is_default': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Payment method added successfully')
        self.assertEqual(data['payment_method']['card_last4'], '4242')
        self.assertNotIn('upi_id', data['payment_method'])

    def test_payment_method_list_returns_success_payload(self):
        user = User.objects.create_user(
            username='paymentlistuser',
            email='paymentlist@example.com',
            password='StrongPass123!',
        )
        rider_profile = RiderProfile.objects.get_or_create(user=user)[0]
        from apps.customers.models import PaymentMethod

        PaymentMethod.objects.create(
            rider=rider_profile,
            type='card',
            card_last4='4242',
            card_brand='Visa',
            card_expiry='12/28',
            card_holder='Bal Reddy',
            is_default=True,
        )

        self.client.force_authenticate(user=user)
        response = self.client.get('/customers/payment-methods/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Payment methods retrieved successfully')
        self.assertEqual(len(data['payment_methods']), 1)


class ProfileViewTests(APITestCase):
    def test_get_profile_returns_success_payload(self):
        user = User.objects.create_user(
            username='profileuser',
            email='profile@example.com',
            password='StrongPass123!',
        )
        rider_profile = RiderProfile.objects.get_or_create(user=user)[0]
        rider_profile.home_address = '45, MG Road, Vijayawada'
        rider_profile.work_address = 'IT Tower, Gachibowli, Hyderabad'
        rider_profile.wallet_balance = 40000
        rider_profile.save()

        self.client.force_authenticate(user=user)
        response = self.client.get('/customers/profile/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Profile retrieved successfully')
        self.assertEqual(data['profile']['wallet_balance_rupees'], 400.0)
        self.assertEqual(data['profile']['rating'], 5.0)
        self.assertEqual(data['profile']['user']['username'], 'profileuser')

    def test_update_profile_returns_success_payload(self):
        user = User.objects.create_user(
            username='profileupdateuser',
            email='profileupdate@example.com',
            password='StrongPass123!',
        )
        RiderProfile.objects.get_or_create(user=user)

        self.client.force_authenticate(user=user)
        response = self.client.patch(
            '/customers/profile/',
            {'home_address': 'Updated Home Address'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Profile updated successfully')
        self.assertEqual(data['profile']['home_address'], 'Updated Home Address')

    def test_put_profile_updates_both_addresses(self):
        user = User.objects.create_user(
            username='profileputuser',
            email='profileput@example.com',
            password='StrongPass123!',
        )
        RiderProfile.objects.get_or_create(user=user)

        self.client.force_authenticate(user=user)
        response = self.client.put(
            '/customers/profile/',
            {
                'home_address': '45, MG Road, Vijayawada',
                'work_address': 'IT Tower, Gachibowli, Hyderabad',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['profile']['home_address'], '45, MG Road, Vijayawada')
        self.assertEqual(data['profile']['work_address'], 'IT Tower, Gachibowli, Hyderabad')

    def test_put_profile_requires_at_least_one_address(self):
        user = User.objects.create_user(
            username='profileemptyuser',
            email='profileempty@example.com',
            password='StrongPass123!',
        )
        RiderProfile.objects.get_or_create(user=user)

        self.client.force_authenticate(user=user)
        response = self.client.put('/customers/profile/', {}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])


class EmergencyContactTests(APITestCase):
    def test_create_returns_success_payload(self):
        user = User.objects.create_user(
            username='emergencyuser',
            email='emergency@example.com',
            password='StrongPass123!',
        )
        RiderProfile.objects.get_or_create(user=user)

        self.client.force_authenticate(user=user)
        response = self.client.post(
            '/customers/emergency-contacts/',
            {
                'name': 'Ravi Kumar',
                'phone': '+919876543210',
                'relationship': 'Customer',
                'is_primary': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Emergency contact added successfully')
        self.assertEqual(data['contact']['name'], 'Ravi Kumar')
        self.assertEqual(data['contact']['phone'], '+919876543210')
        self.assertTrue(data['contact']['is_primary'])

    def test_list_returns_success_payload(self):
        user = User.objects.create_user(
            username='emergencylistuser',
            email='emergencylist@example.com',
            password='StrongPass123!',
        )
        rider_profile = RiderProfile.objects.get_or_create(user=user)[0]
        from apps.customers.models import EmergencyContact

        EmergencyContact.objects.create(
            rider=rider_profile,
            name='Ravi Kumar',
            phone='+919876543210',
            relationship='Customer',
            is_primary=True,
        )

        self.client.force_authenticate(user=user)
        response = self.client.get('/customers/emergency-contacts/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Emergency contacts retrieved successfully')
        self.assertEqual(len(data['contacts']), 1)
        self.assertEqual(data['contacts'][0]['name'], 'Ravi Kumar')

    def test_create_rejects_duplicate_phone(self):
        user = User.objects.create_user(
            username='emergencydupuser',
            email='emergencydup@example.com',
            password='StrongPass123!',
        )
        rider_profile = RiderProfile.objects.get_or_create(user=user)[0]
        from apps.customers.models import EmergencyContact

        EmergencyContact.objects.create(
            rider=rider_profile,
            name='Ravi Kumar',
            phone='+919876543210',
            relationship='Customer',
            is_primary=True,
        )

        self.client.force_authenticate(user=user)
        response = self.client.post(
            '/customers/emergency-contacts/',
            {
                'name': 'Ravi Kumar',
                'phone': '+919876543210',
                'relationship': 'Customer',
                'is_primary': False,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('phone', data['errors'])
