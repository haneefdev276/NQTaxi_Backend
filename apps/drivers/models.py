"""
Drivers app models.

Covers:
  - DriverProfile    : extended driver info (OneToOne → auth.User)
  - Vehicle          : driver vehicle details
  - Document         : KYC / licence documents (S3 key reference)
  - BankDetails      : payout bank account
  - Wallet           : balance ledger
  - Transaction      : credit / debit / withdrawal entries
  - WithdrawalRequest: payout request record
  - DriverLocation   : latest GPS coordinates
  - Incentive        : platform-defined bonus targets
  - DriverIncentiveProgress : per-driver progress toward an incentive
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class DriverStatus(models.TextChoices):
    ONLINE  = 'ONLINE',  'Online'
    OFFLINE = 'OFFLINE', 'Offline'
    BLOCKED = 'BLOCKED', 'Blocked'


class VehicleType(models.TextChoices):
    SEDAN   = 'SEDAN',   'Sedan'
    SUV     = 'SUV',     'SUV'
    AUTO    = 'AUTO',    'Auto Rickshaw'
    BIKE    = 'BIKE',    'Bike'
    MINI    = 'MINI',    'Mini'


class DocumentType(models.TextChoices):
    LICENCE        = 'LICENCE',        "Driver's Licence"
    REGISTRATION   = 'REGISTRATION',   'Vehicle Registration'
    INSURANCE      = 'INSURANCE',      'Insurance Certificate'
    PAN            = 'PAN',            'PAN Card'
    AADHAR         = 'AADHAR',         'Aadhar Card'
    PROFILE_PHOTO  = 'PROFILE_PHOTO',  'Profile Photo'
    OTHER          = 'OTHER',          'Other'


class DocumentStatus(models.TextChoices):
    PENDING  = 'PENDING',  'Pending Review'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class TransactionType(models.TextChoices):
    CREDIT     = 'CREDIT',     'Credit'
    DEBIT      = 'DEBIT',      'Debit'
    WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal'


class WithdrawalStatus(models.TextChoices):
    PENDING    = 'PENDING',    'Pending'
    PROCESSING = 'PROCESSING', 'Processing'
    COMPLETED  = 'COMPLETED',  'Completed'
    FAILED     = 'FAILED',     'Failed'


# ---------------------------------------------------------------------------
# DriverProfile
# ---------------------------------------------------------------------------

class DriverProfile(models.Model):
    user            = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    phone           = models.CharField(max_length=20, blank=True)
    date_of_birth   = models.DateField(null=True, blank=True)
    gender          = models.CharField(max_length=10, blank=True)
    profile_photo   = models.CharField(max_length=512, blank=True, help_text='S3 key of profile photo')
    licence_number  = models.CharField(max_length=50, blank=True)
    licence_expiry  = models.DateField(null=True, blank=True)
    city            = models.CharField(max_length=100, blank=True)
    state           = models.CharField(max_length=100, blank=True)
    status          = models.CharField(max_length=10, choices=DriverStatus.choices, default=DriverStatus.OFFLINE)
    rating          = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_rides     = models.PositiveIntegerField(default=0)
    accepted_rides  = models.PositiveIntegerField(default=0)
    rejected_rides  = models.PositiveIntegerField(default=0)
    is_verified     = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Driver Profile'
        verbose_name_plural = 'Driver Profiles'

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} — {self.status}'

    @property
    def acceptance_rate(self):
        """Return acceptance rate as a float 0-100."""
        total = self.accepted_rides + self.rejected_rides
        if total == 0:
            return 0.0
        return round((self.accepted_rides / total) * 100, 2)


# ---------------------------------------------------------------------------
# Vehicle
# ---------------------------------------------------------------------------

class Vehicle(models.Model):
    driver        = models.OneToOneField(DriverProfile, on_delete=models.CASCADE, related_name='vehicle')
    make          = models.CharField(max_length=100)
    model         = models.CharField(max_length=100)
    year          = models.PositiveSmallIntegerField()
    plate_number  = models.CharField(max_length=20, unique=True)
    color         = models.CharField(max_length=50)
    vehicle_type  = models.CharField(max_length=10, choices=VehicleType.choices, default=VehicleType.SEDAN)
    rc_number     = models.CharField(max_length=50, blank=True, help_text='Registration Certificate number')
    is_verified   = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Vehicle'
        verbose_name_plural = 'Vehicles'

    def __str__(self):
        return f'{self.year} {self.make} {self.model} [{self.plate_number}]'


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

class Document(models.Model):
    driver      = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='documents')
    doc_type    = models.CharField(max_length=20, choices=DocumentType.choices)
    s3_key      = models.CharField(max_length=512, help_text='S3 object key of the uploaded file')
    original_name = models.CharField(max_length=255, blank=True, help_text='Original filename for display')
    status      = models.CharField(max_length=10, choices=DocumentStatus.choices, default=DocumentStatus.PENDING)
    rejection_reason = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name        = 'Document'
        verbose_name_plural = 'Documents'
        ordering            = ['-uploaded_at']

    def __str__(self):
        return f'{self.driver} — {self.get_doc_type_display()} ({self.status})'


# ---------------------------------------------------------------------------
# BankDetails
# ---------------------------------------------------------------------------

class BankDetails(models.Model):
    driver          = models.OneToOneField(DriverProfile, on_delete=models.CASCADE, related_name='bank_details')
    account_holder  = models.CharField(max_length=150)
    account_number  = models.CharField(max_length=30)
    ifsc_code       = models.CharField(max_length=15)
    bank_name       = models.CharField(max_length=150)
    branch_name     = models.CharField(max_length=150, blank=True)
    upi_id          = models.CharField(max_length=100, blank=True)
    is_verified     = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Bank Details'
        verbose_name_plural = 'Bank Details'

    def __str__(self):
        return f'{self.driver} — {self.bank_name} ****{self.account_number[-4:]}'


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------

class Wallet(models.Model):
    driver          = models.OneToOneField(DriverProfile, on_delete=models.CASCADE, related_name='wallet')
    balance         = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_earned    = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_withdrawn = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    currency        = models.CharField(max_length=5, default='INR')
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Wallet'
        verbose_name_plural = 'Wallets'

    def __str__(self):
        return f'{self.driver} — {self.currency} {self.balance}'


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class Transaction(models.Model):
    wallet      = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    txn_type    = models.CharField(max_length=15, choices=TransactionType.choices)
    amount      = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    reference   = models.CharField(max_length=100, blank=True, help_text='Ride ID, withdrawal ID, etc.')
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.txn_type} ₹{self.amount} — {self.wallet.driver}'


# ---------------------------------------------------------------------------
# WithdrawalRequest
# ---------------------------------------------------------------------------

class WithdrawalRequest(models.Model):
    driver          = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='withdrawal_requests')
    amount          = models.DecimalField(max_digits=12, decimal_places=2)
    status          = models.CharField(max_length=15, choices=WithdrawalStatus.choices, default=WithdrawalStatus.PENDING)
    bank_details    = models.ForeignKey(BankDetails, on_delete=models.SET_NULL, null=True, blank=True)
    utr_number      = models.CharField(max_length=100, blank=True, help_text='Unique Transaction Reference from bank')
    failure_reason  = models.TextField(blank=True)
    requested_at    = models.DateTimeField(auto_now_add=True)
    processed_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name        = 'Withdrawal Request'
        verbose_name_plural = 'Withdrawal Requests'
        ordering            = ['-requested_at']

    def __str__(self):
        return f'{self.driver} — ₹{self.amount} ({self.status})'


# ---------------------------------------------------------------------------
# DriverLocation
# ---------------------------------------------------------------------------

class DriverLocation(models.Model):
    driver      = models.OneToOneField(DriverProfile, on_delete=models.CASCADE, related_name='location')
    latitude    = models.DecimalField(max_digits=9, decimal_places=6)
    longitude   = models.DecimalField(max_digits=9, decimal_places=6)
    heading     = models.FloatField(null=True, blank=True, help_text='Compass bearing in degrees (0-360)')
    speed       = models.FloatField(null=True, blank=True, help_text='Speed in km/h')
    updated_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name        = 'Driver Location'
        verbose_name_plural = 'Driver Locations'

    def __str__(self):
        return f'{self.driver} — ({self.latitude}, {self.longitude})'


# ---------------------------------------------------------------------------
# Incentive
# ---------------------------------------------------------------------------

class Incentive(models.Model):
    title           = models.CharField(max_length=150)
    description     = models.TextField(blank=True)
    target_rides    = models.PositiveIntegerField(help_text='Number of rides to complete to earn the bonus')
    bonus_amount    = models.DecimalField(max_digits=10, decimal_places=2)
    is_active       = models.BooleanField(default=True)
    start_date      = models.DateField()
    end_date        = models.DateField()
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Incentive'
        verbose_name_plural = 'Incentives'
        ordering            = ['-start_date']

    def __str__(self):
        return f'{self.title} (target={self.target_rides} rides, bonus=₹{self.bonus_amount})'


# ---------------------------------------------------------------------------
# DriverIncentiveProgress
# ---------------------------------------------------------------------------

class DriverIncentiveProgress(models.Model):
    driver          = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='incentive_progress')
    incentive       = models.ForeignKey(Incentive, on_delete=models.CASCADE, related_name='driver_progress')
    rides_completed = models.PositiveIntegerField(default=0)
    is_claimed      = models.BooleanField(default=False)
    claimed_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name        = 'Driver Incentive Progress'
        verbose_name_plural = 'Driver Incentive Progress'
        unique_together     = ('driver', 'incentive')

    def __str__(self):
        return f'{self.driver} — {self.incentive.title} ({self.rides_completed}/{self.incentive.target_rides})'

    @property
    def progress_percent(self):
        if self.incentive.target_rides == 0:
            return 100
        return min(round((self.rides_completed / self.incentive.target_rides) * 100, 1), 100)
