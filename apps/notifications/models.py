from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Notification(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default='')
    notification_type = models.CharField(max_length=50)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['is_read', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f'{self.title} ({self.user_id})'


class FCMDeviceToken(BaseModel):
    DEVICE_ANDROID = 'android'
    DEVICE_IOS = 'ios'
    DEVICE_CHOICES = [
        (DEVICE_ANDROID, 'Android'),
        (DEVICE_IOS, 'iOS'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fcm_tokens',
    )
    token = models.CharField(max_length=512, unique=True)
    device_type = models.CharField(max_length=20, choices=DEVICE_CHOICES, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'fcm_device_tokens'

    def __str__(self):
        return f'{self.device_type or "device"} token for {self.user_id}'
