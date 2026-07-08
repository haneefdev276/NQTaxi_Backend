from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.notifications.models import FCMDeviceToken, Notification

User = get_user_model()


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='notifyuser',
            email='notify@example.com',
            password='StrongPass123!',
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='StrongPass123!',
        )
        self.client.force_authenticate(user=self.user)

        self.read_notification = Notification.objects.create(
            user=self.user,
            title='Read alert',
            body='Already seen',
            notification_type='trip_update',
            is_read=True,
            read_at=timezone.now(),
        )
        self.unread_notification = Notification.objects.create(
            user=self.user,
            title='Unread alert',
            body='New trip update',
            notification_type='trip_update',
        )
        self.other_notification = Notification.objects.create(
            user=self.other_user,
            title='Other user alert',
            body='Should not appear',
            notification_type='promo',
        )

    def test_list_notifications_unread_first(self):
        response = self.client.get('/api/v1/notifications/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Notifications retrieved successfully')
        self.assertEqual(data['unread_count'], 1)
        self.assertEqual(len(data['notifications']), 2)
        self.assertEqual(data['notifications'][0]['id'], str(self.unread_notification.pk))
        self.assertFalse(data['notifications'][0]['is_read'])

    def test_list_notifications_empty_state(self):
        Notification.objects.filter(user=self.user).delete()
        response = self.client.get('/api/v1/notifications/?page=1')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'No notifications found')
        self.assertEqual(data['notifications'], [])
        self.assertEqual(data['unread_count'], 0)
        self.assertEqual(data['count'], 0)
        self.assertIsNone(data['next'])
        self.assertIsNone(data['previous'])

    def test_mark_single_notification_as_read(self):
        response = self.client.patch(f'/api/v1/notifications/{self.unread_notification.pk}/read/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['notification']['is_read'])
        self.unread_notification.refresh_from_db()
        self.assertTrue(self.unread_notification.is_read)
        self.assertIsNotNone(self.unread_notification.read_at)

    def test_mark_single_notification_idempotent_when_already_read(self):
        response = self.client.patch(f'/api/v1/notifications/{self.read_notification.pk}/read/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertTrue(response.json()['notification']['is_read'])

    def test_cannot_mark_other_users_notification(self):
        response = self.client.patch(f'/api/v1/notifications/{self.other_notification.pk}/read/')

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'NOTIFICATION_NOT_FOUND')

    def test_mark_nonexistent_notification_returns_structured_error(self):
        response = self.client.patch('/api/v1/notifications/b803ad2c-a3b0-4d92-a533-88414e97c11e/read/')

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Notification not found.')
        self.assertEqual(data['code'], 'NOTIFICATION_NOT_FOUND')

    def test_mark_all_notifications_as_read(self):
        response = self.client.post('/api/v1/notifications/read-all/', {}, format='json')

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'All notifications marked as read')
        self.assertEqual(data['updated_count'], 1)
        self.assertEqual(data['unread_count'], 0)
        self.assertEqual(data['total_count'], 2)
        self.assertEqual(
            Notification.objects.filter(user=self.user, is_read=False).count(),
            0,
        )

    def test_mark_all_notifications_when_already_read(self):
        Notification.objects.filter(user=self.user).update(is_read=True, read_at=timezone.now())
        response = self.client.post('/api/v1/notifications/read-all/', {'confirm': True}, format='json')

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'All notifications already marked as read')
        self.assertEqual(data['updated_count'], 0)
        self.assertEqual(data['total_count'], 2)

    def test_register_fcm_token(self):
        response = self.client.post(
            '/api/v1/notifications/fcm-token/',
            {
                'token': 'fcm-token-abc123',
                'device_type': 'android',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['fcm_token']['token'], 'fcm-token-abc123')
        self.assertTrue(
            FCMDeviceToken.objects.filter(user=self.user, token='fcm-token-abc123', is_active=True).exists()
        )

    def test_register_fcm_token_reassigns_existing_token(self):
        FCMDeviceToken.objects.create(
            user=self.other_user,
            token='shared-device-token',
            device_type='ios',
        )

        response = self.client.post(
            '/api/v1/notifications/fcm-token/',
            {
                'token': 'shared-device-token',
                'device_type': 'ios',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        token = FCMDeviceToken.objects.get(token='shared-device-token')
        self.assertEqual(token.user_id, self.user.id)
        self.assertTrue(token.is_active)
