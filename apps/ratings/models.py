import uuid

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.trips.models import Trip


class Rating(BaseModel):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='ratings')
    given_by_rider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings_given')
    score = models.DecimalField(max_digits=3, decimal_places=2)
    comment = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ratings'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.score} for {self.trip_id}'
