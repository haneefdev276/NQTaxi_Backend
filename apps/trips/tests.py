"""
End-to-end tests for the Trips / Rides API.

Covers every endpoint under /api/v1/rides/ including:
  - Trip request
  - List / detail / active
  - Accept, reject, start (with OTP), complete, cancel
  - Nearby drivers
  - State machine guard rails (invalid transitions)
  - Permission checks (unauthenticated, wrong role)

Run with:
    python manage.py test apps.trips.tests --verbosity=2
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.trips.models import Trip
from apps.drivers.models import DriverProfile, DriverLocation, DriverStatus
from apps.customers.models import RiderProfile

User = get_user_model()

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

TRIP_PAYLOAD = {
    'pickup_address':   'MG Road, Bangalore',
    'pickup_latitude':  '12.975109',
    'pickup_longitude': '77.607437',
    'drop_address':     'Indiranagar, Bangalore',
    'drop_latitude':    '12.978728',
    'drop_longitude':   '77.638962',
}


def _token(user) -> str:
    """Return a Bearer token string for the given user."""
    return str(RefreshToken.for_user(user).access_token)


def _auth(user) -> dict:
    """Return Authorization header dict."""
    return {'HTTP_AUTHORIZATION': f'Bearer {_token(user)}'}


# ─────────────────────────────────────────────────────────────────────────────
# Base setup
# ─────────────────────────────────────────────────────────────────────────────

class TripTestBase(APITestCase):
    """
    Creates:
      - self.rider_user  + RiderProfile
      - self.driver_user + DriverProfile (+ DriverLocation)
    """

    def setUp(self):
        # ── Rider ──────────────────────────────────────────────────────────
        self.rider_user = User.objects.create_user(
            username='test_rider',
            password='TestPass123!',
            phone='+919000000001',
            role='rider',
        )
        self.rider_profile = RiderProfile.objects.create(user=self.rider_user)

        # ── Driver ─────────────────────────────────────────────────────────
        self.driver_user = User.objects.create_user(
            username='test_driver',
            password='TestPass123!',
            phone='+919000000002',
            role='driver',
        )
        self.driver_profile = DriverProfile.objects.create(
            user=self.driver_user,
            status=DriverStatus.ONLINE,
            phone='+919000000002',
        )
        # Give the driver a location so nearby-drivers works
        DriverLocation.objects.create(
            driver=self.driver_profile,
            latitude='12.975500',
            longitude='77.607000',
        )

    # ── Convenience helpers ────────────────────────────────────────────────

    def _request_trip(self) -> Trip:
        """Create a REQUESTED trip as the rider and return the Trip object."""
        url = reverse('rides:trip-request')
        resp = self.client.post(url, TRIP_PAYLOAD, format='json', **_auth(self.rider_user))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.json())
        return Trip.objects.get(pk=resp.json()['id'])

    def _accept_trip(self, trip: Trip) -> Trip:
        url = reverse('rides:trip-accept', kwargs={'pk': trip.pk})
        resp = self.client.post(url, format='json', **_auth(self.driver_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.json())
        trip.refresh_from_db()
        return trip

    def _start_trip(self, trip: Trip) -> Trip:
        trip.refresh_from_db()
        url = reverse('rides:trip-start', kwargs={'pk': trip.pk})
        resp = self.client.post(url, {'otp': trip.otp}, format='json', **_auth(self.driver_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.json())
        trip.refresh_from_db()
        return trip


# ─────────────────────────────────────────────────────────────────────────────
# 1. Trip Request
# ─────────────────────────────────────────────────────────────────────────────

class TripRequestTests(TripTestBase):

    def test_rider_can_request_trip(self):
        """POST /rides/request/ creates a REQUESTED trip."""
        url = reverse('rides:trip-request')
        resp = self.client.post(url, TRIP_PAYLOAD, format='json', **_auth(self.rider_user))

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.json()
        self.assertEqual(data['status'], 'REQUESTED')
        self.assertIsNotNone(data['otp'])
        self.assertEqual(len(data['otp']), 6)

    def test_driver_cannot_request_trip(self):
        """Drivers do not have a rider_profile — should get 403."""
        url = reverse('rides:trip-request')
        resp = self.client.post(url, TRIP_PAYLOAD, format='json', **_auth(self.driver_user))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_request_trip(self):
        url = reverse('rides:trip-request')
        resp = self.client.post(url, TRIP_PAYLOAD, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rider_cannot_have_two_active_trips(self):
        """A rider with an active trip cannot request another."""
        self._request_trip()
        url = reverse('rides:trip-request')
        resp = self.client.post(url, TRIP_PAYLOAD, format='json', **_auth(self.rider_user))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        err_body = resp.json()
        # DRF non-field errors come back as {'non_field_errors': ['...']}
        errors = err_body.get('non_field_errors', err_body.get('detail', ['']))
        error_text = errors[0] if isinstance(errors, list) else str(errors)
        self.assertIn('active trip', error_text.lower())


# ─────────────────────────────────────────────────────────────────────────────
# 2. Trip List & Detail
# ─────────────────────────────────────────────────────────────────────────────

class TripListDetailTests(TripTestBase):

    def test_rider_sees_own_trips(self):
        """GET /rides/ returns the rider's own trips."""
        self._request_trip()
        url = reverse('rides:trip-list')
        resp = self.client.get(url, **_auth(self.rider_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['count'], 1)

    def test_driver_sees_own_trips(self):
        """Driver list is empty before accepting any trip."""
        url = reverse('rides:trip-list')
        resp = self.client.get(url, **_auth(self.driver_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['count'], 0)

    def test_trip_detail_visible_to_rider(self):
        trip = self._request_trip()
        url = reverse('rides:trip-detail', kwargs={'pk': trip.pk})
        resp = self.client.get(url, **_auth(self.rider_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(str(resp.json()['id']), str(trip.pk))

    def test_trip_detail_hidden_from_unrelated_user(self):
        """A second rider cannot view another rider's trip."""
        trip = self._request_trip()
        other_rider = User.objects.create_user(
            username='other_rider', password='Pass123!', phone='+919000000099', role='rider'
        )
        RiderProfile.objects.create(user=other_rider)
        url = reverse('rides:trip-detail', kwargs={'pk': trip.pk})
        resp = self.client.get(url, **_auth(other_rider))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_status(self):
        self._request_trip()
        url = reverse('rides:trip-list')
        resp = self.client.get(url, {'status': 'REQUESTED'}, **_auth(self.rider_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['count'], 1)

        resp2 = self.client.get(url, {'status': 'COMPLETED'}, **_auth(self.rider_user))
        self.assertEqual(resp2.json()['count'], 0)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Active Trip
# ─────────────────────────────────────────────────────────────────────────────

class ActiveTripTests(TripTestBase):

    def test_no_active_trip_returns_204(self):
        url = reverse('rides:trip-active')
        resp = self.client.get(url, **_auth(self.rider_user))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_active_trip_returned_after_request(self):
        self._request_trip()
        url = reverse('rides:trip-active')
        resp = self.client.get(url, **_auth(self.rider_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['status'], 'REQUESTED')


# ─────────────────────────────────────────────────────────────────────────────
# 4. Accept
# ─────────────────────────────────────────────────────────────────────────────

class TripAcceptTests(TripTestBase):

    def test_driver_can_accept_requested_trip(self):
        trip = self._request_trip()
        url = reverse('rides:trip-accept', kwargs={'pk': trip.pk})
        resp = self.client.post(url, format='json', **_auth(self.driver_user))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data['status'], 'ACCEPTED')
        self.assertIsNotNone(data['accepted_at'])

        # Stats updated
        self.driver_profile.refresh_from_db()
        self.assertEqual(self.driver_profile.accepted_rides, 1)

    def test_rider_cannot_accept_trip(self):
        trip = self._request_trip()
        url = reverse('rides:trip-accept', kwargs={'pk': trip.pk})
        resp = self.client.post(url, format='json', **_auth(self.rider_user))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_accept_already_accepted_trip(self):
        trip = self._request_trip()
        self._accept_trip(trip)

        url = reverse('rides:trip-accept', kwargs={'pk': trip.pk})
        resp = self.client.post(url, format='json', **_auth(self.driver_user))
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Reject
# ─────────────────────────────────────────────────────────────────────────────

class TripRejectTests(TripTestBase):

    def test_driver_can_reject_requested_trip(self):
        trip = self._request_trip()
        url = reverse('rides:trip-reject', kwargs={'pk': trip.pk})
        resp = self.client.post(url, format='json', **_auth(self.driver_user))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('rejected', resp.json()['detail'].lower())

        # Trip stays REQUESTED
        trip.refresh_from_db()
        self.assertEqual(trip.status, 'REQUESTED')

        # Stats updated
        self.driver_profile.refresh_from_db()
        self.assertEqual(self.driver_profile.rejected_rides, 1)

    def test_cannot_reject_accepted_trip(self):
        trip = self._request_trip()
        self._accept_trip(trip)
        url = reverse('rides:trip-reject', kwargs={'pk': trip.pk})
        resp = self.client.post(url, format='json', **_auth(self.driver_user))
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Start
# ─────────────────────────────────────────────────────────────────────────────

class TripStartTests(TripTestBase):

    def test_driver_can_start_trip_with_correct_otp(self):
        trip = self._request_trip()
        self._accept_trip(trip)
        trip.refresh_from_db()

        url = reverse('rides:trip-start', kwargs={'pk': trip.pk})
        resp = self.client.post(url, {'otp': trip.otp}, format='json', **_auth(self.driver_user))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['status'], 'ONGOING')
        self.assertIsNotNone(resp.json()['started_at'])
        # OTP should be cleared
        self.assertEqual(resp.json()['otp'], '')

    def test_wrong_otp_rejected(self):
        trip = self._request_trip()
        self._accept_trip(trip)
        url = reverse('rides:trip-start', kwargs={'pk': trip.pk})
        resp = self.client.post(url, {'otp': '000000'}, format='json', **_auth(self.driver_user))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_otp_rejected(self):
        trip = self._request_trip()
        self._accept_trip(trip)
        url = reverse('rides:trip-start', kwargs={'pk': trip.pk})
        resp = self.client.post(url, {}, format='json', **_auth(self.driver_user))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_start_unaccepted_trip(self):
        """REQUESTED trip cannot be started — must be ACCEPTED first."""
        trip = self._request_trip()
        url = reverse('rides:trip-start', kwargs={'pk': trip.pk})
        resp = self.client.post(url, {'otp': trip.otp}, format='json', **_auth(self.driver_user))
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_unassigned_driver_cannot_start(self):
        """A different driver cannot start a trip assigned to someone else."""
        trip = self._request_trip()
        self._accept_trip(trip)

        other_driver_user = User.objects.create_user(
            username='driver2', password='Pass123!', phone='+919000000003', role='driver'
        )
        DriverProfile.objects.create(user=other_driver_user, phone='+919000000003')
        trip.refresh_from_db()

        url = reverse('rides:trip-start', kwargs={'pk': trip.pk})
        resp = self.client.post(url, {'otp': trip.otp}, format='json', **_auth(other_driver_user))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Complete
# ─────────────────────────────────────────────────────────────────────────────

class TripCompleteTests(TripTestBase):

    def _get_ongoing_trip(self) -> Trip:
        trip = self._request_trip()
        self._accept_trip(trip)
        self._start_trip(trip)
        return trip

    def test_driver_can_complete_ongoing_trip(self):
        trip = self._get_ongoing_trip()
        url = reverse('rides:trip-complete', kwargs={'pk': trip.pk})
        payload = {'fare': '185.50', 'distance_km': '8.2'}
        resp = self.client.post(url, payload, format='json', **_auth(self.driver_user))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data['status'], 'COMPLETED')
        self.assertEqual(data['fare'], '185.50')
        self.assertEqual(data['distance_km'], '8.20')
        self.assertIsNotNone(data['completed_at'])

    def test_driver_stats_updated_on_complete(self):
        trip = self._get_ongoing_trip()
        url = reverse('rides:trip-complete', kwargs={'pk': trip.pk})
        self.client.post(url, {'fare': '100.00'}, format='json', **_auth(self.driver_user))

        self.driver_profile.refresh_from_db()
        self.assertEqual(self.driver_profile.total_rides, 1)

    def test_driver_wallet_credited_on_complete(self):
        trip = self._get_ongoing_trip()
        url = reverse('rides:trip-complete', kwargs={'pk': trip.pk})
        self.client.post(url, {'fare': '250.00'}, format='json', **_auth(self.driver_user))

        from apps.drivers.models import Wallet
        wallet = Wallet.objects.get(driver=self.driver_profile)
        self.assertEqual(wallet.balance, Decimal('250.00'))
        self.assertEqual(wallet.total_earned, Decimal('250.00'))

    def test_rider_total_rides_incremented(self):
        trip = self._get_ongoing_trip()
        url = reverse('rides:trip-complete', kwargs={'pk': trip.pk})
        self.client.post(url, {'fare': '150.00'}, format='json', **_auth(self.driver_user))

        self.rider_profile.refresh_from_db()
        self.assertEqual(self.rider_profile.total_rides, 1)

    def test_cannot_complete_requested_trip(self):
        trip = self._request_trip()
        url = reverse('rides:trip-complete', kwargs={'pk': trip.pk})
        resp = self.client.post(url, {'fare': '100'}, format='json', **_auth(self.driver_user))
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_cannot_complete_without_being_assigned_driver(self):
        trip = self._get_ongoing_trip()
        other = User.objects.create_user(
            username='driver3', password='Pass!', phone='+919000000004', role='driver'
        )
        DriverProfile.objects.create(user=other, phone='+919000000004')

        url = reverse('rides:trip-complete', kwargs={'pk': trip.pk})
        resp = self.client.post(url, {'fare': '100'}, format='json', **_auth(other))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Cancel
# ─────────────────────────────────────────────────────────────────────────────

class TripCancelTests(TripTestBase):

    def test_rider_can_cancel_requested_trip(self):
        trip = self._request_trip()
        url = reverse('rides:trip-cancel', kwargs={'pk': trip.pk})
        resp = self.client.post(url, {'reason': 'Changed plans'}, format='json', **_auth(self.rider_user))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data['status'], 'CANCELLED')
        self.assertEqual(data['cancelled_by'], 'RIDER')
        self.assertEqual(data['cancellation_reason'], 'Changed plans')

    def test_driver_can_cancel_accepted_trip(self):
        trip = self._request_trip()
        self._accept_trip(trip)
        url = reverse('rides:trip-cancel', kwargs={'pk': trip.pk})
        resp = self.client.post(url, {'reason': 'Emergency'}, format='json', **_auth(self.driver_user))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['cancelled_by'], 'DRIVER')

    def test_cannot_cancel_completed_trip(self):
        trip = self._request_trip()
        self._accept_trip(trip)
        self._start_trip(trip)
        url_complete = reverse('rides:trip-complete', kwargs={'pk': trip.pk})
        self.client.post(url_complete, {'fare': '100'}, format='json', **_auth(self.driver_user))

        url_cancel = reverse('rides:trip-cancel', kwargs={'pk': trip.pk})
        resp = self.client.post(url_cancel, format='json', **_auth(self.rider_user))
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_unrelated_user_cannot_cancel(self):
        trip = self._request_trip()
        other = User.objects.create_user(
            username='random_rider', password='Pass!', phone='+919000000005', role='rider'
        )
        RiderProfile.objects.create(user=other)

        url = reverse('rides:trip-cancel', kwargs={'pk': trip.pk})
        resp = self.client.post(url, format='json', **_auth(other))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancel_without_reason_works(self):
        """reason field is optional."""
        trip = self._request_trip()
        url = reverse('rides:trip-cancel', kwargs={'pk': trip.pk})
        resp = self.client.post(url, {}, format='json', **_auth(self.rider_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['cancellation_reason'], '')


# ─────────────────────────────────────────────────────────────────────────────
# 9. Full Lifecycle (Happy Path)
# ─────────────────────────────────────────────────────────────────────────────

class TripFullLifecycleTest(TripTestBase):

    def test_full_happy_path(self):
        """
        REQUESTED → ACCEPTED → ONGOING → COMPLETED
        Asserts final state and wallet balance.
        """
        # Step 1: Rider requests
        trip = self._request_trip()
        self.assertEqual(trip.status, 'REQUESTED')

        # Step 2: Driver accepts
        self._accept_trip(trip)
        trip.refresh_from_db()
        self.assertEqual(trip.status, 'ACCEPTED')

        # Step 3: Driver starts (with OTP)
        self._start_trip(trip)
        trip.refresh_from_db()
        self.assertEqual(trip.status, 'ONGOING')

        # Step 4: Driver completes
        url = reverse('rides:trip-complete', kwargs={'pk': trip.pk})
        resp = self.client.post(
            url,
            {'fare': '320.00', 'distance_km': '14.5'},
            format='json',
            **_auth(self.driver_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        trip.refresh_from_db()
        self.assertEqual(trip.status, 'COMPLETED')
        self.assertEqual(trip.fare, Decimal('320.00'))

        # Wallet check
        from apps.drivers.models import Wallet
        wallet = Wallet.objects.get(driver=self.driver_profile)
        self.assertEqual(wallet.balance, Decimal('320.00'))

        # Stats check
        self.driver_profile.refresh_from_db()
        self.assertEqual(self.driver_profile.total_rides, 1)
        self.assertEqual(self.driver_profile.accepted_rides, 1)

        self.rider_profile.refresh_from_db()
        self.assertEqual(self.rider_profile.total_rides, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 10. Nearby Drivers
# ─────────────────────────────────────────────────────────────────────────────

class NearbyDriversTests(TripTestBase):

    def test_rider_can_find_nearby_drivers(self):
        url = reverse('rides:nearby-drivers')
        resp = self.client.get(
            url,
            {'latitude': '12.975109', 'longitude': '77.607437'},
            **_auth(self.rider_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        # Results sorted by distance
        if len(data) > 1:
            self.assertLessEqual(data[0]['distance_km'], data[1]['distance_km'])

    def test_missing_coordinates_returns_400(self):
        url = reverse('rides:nearby-drivers')
        resp = self.client.get(url, **_auth(self.rider_user))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_driver_cannot_access_nearby_drivers(self):
        url = reverse('rides:nearby-drivers')
        resp = self.client.get(
            url,
            {'latitude': '12.975109', 'longitude': '77.607437'},
            **_auth(self.driver_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_limit_query_param_respected(self):
        # Create 3 more online drivers
        for i in range(3):
            u = User.objects.create_user(
                username=f'xdriver{i}', password='Pass!',
                phone=f'+91900000010{i}', role='driver',
            )
            dp = DriverProfile.objects.create(user=u, status=DriverStatus.ONLINE)
            DriverLocation.objects.create(driver=dp, latitude='12.975000', longitude='77.607000')

        url = reverse('rides:nearby-drivers')
        resp = self.client.get(
            url,
            {'latitude': '12.975109', 'longitude': '77.607437', 'limit': '2'},
            **_auth(self.rider_user),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(resp.json()), 2)
