"""
Trip model — represents the full lifecycle of a ride.

State machine:
    REQUESTED → ACCEPTED  (driver accepts)
    REQUESTED → CANCELLED (rider cancels before acceptance)
    ACCEPTED  → ONGOING   (driver starts the trip)
    ACCEPTED  → CANCELLED (driver or rider cancels)
    ONGOING   → COMPLETED (driver completes the trip)
    ONGOING   → CANCELLED (emergency cancel)
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class Trip(BaseModel):
    class Status(models.TextChoices):
        REQUESTED = 'REQUESTED', 'Requested'
        ACCEPTED  = 'ACCEPTED',  'Accepted'
        ONGOING   = 'ONGOING',   'Ongoing'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class CancelledBy(models.TextChoices):
        RIDER  = 'RIDER',  'Rider'
        DRIVER = 'DRIVER', 'Driver'
        SYSTEM = 'SYSTEM', 'System'

    # -----------------------------------------------------------------------
    # Participants
    # -----------------------------------------------------------------------
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trips_as_rider',
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='trips_as_driver',
    )

    # -----------------------------------------------------------------------
    # Location
    # -----------------------------------------------------------------------
    pickup_address   = models.CharField(max_length=500)
    pickup_latitude  = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)

    drop_address   = models.CharField(max_length=500)
    drop_latitude  = models.DecimalField(max_digits=9, decimal_places=6)
    drop_longitude = models.DecimalField(max_digits=9, decimal_places=6)

    # -----------------------------------------------------------------------
    # Fare & Distance
    # -----------------------------------------------------------------------
    fare         = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    distance_km  = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # -----------------------------------------------------------------------
    # Status & Timestamps
    # -----------------------------------------------------------------------
    status       = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )
    requested_at = models.DateTimeField(default=timezone.now)
    accepted_at  = models.DateTimeField(null=True, blank=True)
    started_at   = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # -----------------------------------------------------------------------
    # Cancellation
    # -----------------------------------------------------------------------
    cancelled_by        = models.CharField(
        max_length=10,
        choices=CancelledBy.choices,
        null=True, blank=True,
    )
    cancellation_reason = models.TextField(blank=True, default='')

    # -----------------------------------------------------------------------
    # OTP for trip start verification (driver shows OTP to rider)
    # -----------------------------------------------------------------------
    otp = models.CharField(max_length=6, blank=True, default='')

    class Meta:
        db_table = 'trips'
        ordering = ['-requested_at']

    def __str__(self):
        return f'Trip {self.pk} | {self.rider} → {self.status}'

    def generate_otp(self):
        """Generate and save a 6-digit OTP for trip start."""
        import random
        self.otp = str(random.randint(100000, 999999))
        self.save(update_fields=['otp'])
        return self.otp
