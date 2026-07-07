import uuid

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class RiderProfile(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rider_profile')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_rides = models.IntegerField(default=0)
    wallet_balance = models.BigIntegerField(default=0)
    home_address = models.CharField(max_length=500, blank=True, null=True)
    work_address = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'rider_profiles'

    def __str__(self):
        return str(self.user)


class PaymentMethod(BaseModel):
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name='payment_methods')
    type = models.CharField(max_length=10, choices=[('card', 'card'), ('upi', 'upi'), ('wallet', 'wallet')])
    card_last4 = models.CharField(max_length=4, blank=True, null=True)
    card_brand = models.CharField(max_length=20, blank=True, null=True)
    card_expiry = models.CharField(max_length=7, blank=True, null=True)
    card_holder = models.CharField(max_length=150, blank=True, null=True)
    upi_id = models.CharField(max_length=100, blank=True, null=True)
    upi_name = models.CharField(max_length=150, blank=True, null=True)
    razorpay_token = models.CharField(max_length=255, blank=True, null=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'payment_methods'


class SavedPlace(BaseModel):
    class LabelChoices(models.TextChoices):
        HOME = 'home', 'Home'
        WORK = 'work', 'Work'
        OTHER = 'other', 'Other'

    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name='saved_places')
    label = models.CharField(max_length=20)
    name = models.CharField(max_length=150, blank=True, null=True)
    address = models.CharField(max_length=500)
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)

    class Meta:
        db_table = 'saved_places'
        constraints = [
            models.UniqueConstraint(
                fields=['rider', 'label'],
                condition=models.Q(label__in=['home', 'work']),
                name='unique_home_work_saved_place_per_rider',
            ),
        ]


class EmergencyContact(BaseModel):
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15)
    relationship = models.CharField(max_length=50, blank=True, null=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = 'emergency_contacts'


class WalletTransaction(BaseModel):
    class TransactionType(models.TextChoices):
        CREDIT = 'credit', 'Credit'
        DEBIT = 'debit', 'Debit'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name='wallet_transactions')
    type = models.CharField(max_length=10, choices=TransactionType.choices)
    amount = models.BigIntegerField()
    description = models.CharField(max_length=255, blank=True, default='')
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    class Meta:
        db_table = 'wallet_transactions'
        ordering = ['-created_at']
