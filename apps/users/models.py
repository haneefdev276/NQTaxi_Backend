import uuid

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class UserProfile(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    phone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.user.get_username()
