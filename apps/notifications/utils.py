from apps.notifications.models import Notification


def create_notification(user, title, body='', notification_type='general', data=None):
    return Notification.objects.create(
        user=user,
        title=title,
        body=body,
        notification_type=notification_type,
        data=data or {},
    )


def ensure_welcome_notification(user):
    if Notification.objects.filter(user=user).exists():
        return None

    return create_notification(
        user=user,
        title='Welcome to NQTaxi',
        body='Your notification feed is ready. Trip and wallet updates will appear here.',
        notification_type='welcome',
    )
