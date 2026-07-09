"""
Serializers for the drivers app.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import (
    DriverProfile, Vehicle, Document, BankDetails,
    Wallet, Transaction, WithdrawalRequest,
    DriverLocation, Incentive, DriverIncentiveProgress,
    DriverStatus, VehicleType, DocumentType, DocumentStatus,
    TransactionType, WithdrawalStatus,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Nested user serializer (read-only)
# ---------------------------------------------------------------------------

class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = fields


# ---------------------------------------------------------------------------
# DriverProfile
# ---------------------------------------------------------------------------

class DriverProfileSerializer(serializers.ModelSerializer):
    user             = UserBasicSerializer(read_only=True)
    acceptance_rate  = serializers.FloatField(read_only=True, help_text="Acceptance rate as a float 0–100.")
    status_display   = serializers.CharField(source='get_status_display', read_only=True, help_text="Human-readable status label.")

    class Meta:
        model  = DriverProfile
        fields = [
            'id', 'user', 'phone', 'date_of_birth', 'gender', 'profile_photo',
            'licence_number', 'licence_expiry', 'city', 'state',
            'status', 'status_display', 'rating', 'total_rides',
            'accepted_rides', 'rejected_rides', 'acceptance_rate',
            'is_verified', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'status', 'rating', 'total_rides',
            'accepted_rides', 'rejected_rides', 'is_verified',
            'created_at', 'updated_at',
        ]


class DriverProfileUpdateSerializer(serializers.ModelSerializer):
    """Used for PATCH — only editable personal fields."""
    class Meta:
        model  = DriverProfile
        fields = [
            'phone', 'date_of_birth', 'gender', 'profile_photo',
            'licence_number', 'licence_expiry', 'city', 'state',
        ]
        extra_kwargs = {
            'phone':           {'help_text': 'Contact phone number of the driver.'},
            'date_of_birth':   {'help_text': 'Date of birth in YYYY-MM-DD format.'},
            'gender':          {'help_text': 'Gender of the driver (e.g. Male, Female, Other).'},
            'profile_photo':   {'help_text': 'S3 key of the profile photo.'},
            'licence_number':  {'help_text': "Driver's licence number."},
            'licence_expiry':  {'help_text': "Driver's licence expiry date in YYYY-MM-DD format."},
            'city':            {'help_text': 'City where the driver operates.'},
            'state':           {'help_text': 'State where the driver operates.'},
        }


# ---------------------------------------------------------------------------
# Vehicle
# ---------------------------------------------------------------------------

class VehicleSerializer(serializers.ModelSerializer):
    vehicle_type_display = serializers.CharField(
        source='get_vehicle_type_display', read_only=True,
        help_text="Human-readable vehicle type label."
    )

    class Meta:
        model  = Vehicle
        fields = [
            'id', 'make', 'model', 'year', 'plate_number', 'color',
            'vehicle_type', 'vehicle_type_display', 'rc_number',
            'is_verified', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_verified', 'created_at', 'updated_at']
        extra_kwargs = {
            'make':         {'help_text': 'Vehicle manufacturer (e.g. Maruti, Honda).'},
            'model':        {'help_text': 'Vehicle model name (e.g. Swift Dzire, City).'},
            'year':         {'help_text': 'Year of manufacture (e.g. 2022).'},
            'plate_number': {'help_text': 'Vehicle registration plate number (must be unique).'},
            'color':        {'help_text': 'Color of the vehicle.'},
            'vehicle_type': {
                'help_text': (
                    f"Type of vehicle. Choices: "
                    f"{', '.join([f'{c[0]} ({c[1]})' for c in VehicleType.choices])}."
                )
            },
            'rc_number':    {'help_text': 'Registration Certificate (RC) number.'},
        }


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

class DocumentSerializer(serializers.ModelSerializer):
    doc_type_display  = serializers.CharField(
        source='get_doc_type_display', read_only=True,
        help_text="Human-readable document type label."
    )
    status_display    = serializers.CharField(
        source='get_status_display', read_only=True,
        help_text="Human-readable document status label."
    )
    file_url = serializers.SerializerMethodField(help_text='URL to download the uploaded document.')

    class Meta:
        model  = Document
        fields = [
            'id', 'doc_type', 'doc_type_display', 'file_url',
            's3_key', 'original_name',
            'status', 'status_display', 'rejection_reason',
            'uploaded_at', 'reviewed_at',
        ]
        read_only_fields = ['id', 'status', 'rejection_reason', 'uploaded_at', 'reviewed_at']

    def get_file_url(self, obj) -> str | None:
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class DocumentUploadSerializer(serializers.Serializer):
    """
    Used for POST /documents/upload/
    Accepts a multipart form upload: doc_type + file.
    Creates and returns the Document record.
    """
    doc_type = serializers.ChoiceField(
        choices=DocumentType.choices,
        help_text=(
            f"Document type. Choices: "
            f"{', '.join([f'{c[0]} ({c[1]})' for c in DocumentType.choices])}."
        ),
    )
    file = serializers.FileField(
        help_text='The document file to upload (PDF, PNG, JPG, etc.). Max size: 5 MB.',
    )

    def validate_file(self, value):
        max_size = 5 * 1024 * 1024  # 5 MB
        if value.size > max_size:
            raise serializers.ValidationError('File size must not exceed 5 MB.')
        return value

    def save(self, driver):
        """Create and return a Document record with the uploaded file."""
        file = self.validated_data['file']
        doc = Document.objects.create(
            driver=driver,
            doc_type=self.validated_data['doc_type'],
            file=file,
            original_name=file.name,
            s3_key='',  # reserved for S3 uploads
        )
        return doc


# ---------------------------------------------------------------------------
# BankDetails
# ---------------------------------------------------------------------------

class BankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BankDetails
        fields = [
            'id', 'account_holder', 'account_number', 'ifsc_code',
            'bank_name', 'branch_name', 'upi_id', 'is_verified',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_verified', 'created_at', 'updated_at']
        extra_kwargs = {
            'account_holder': {'help_text': 'Full name of the account holder.'},
            'account_number': {'help_text': 'Bank account number.'},
            'ifsc_code':      {'help_text': 'IFSC code of the bank branch.'},
            'bank_name':      {'help_text': 'Name of the bank.'},
            'branch_name':    {'help_text': 'Name of the bank branch (optional).'},
            'upi_id':         {'help_text': 'UPI ID for instant payments (optional).'},
        }


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class TransactionSerializer(serializers.ModelSerializer):
    txn_type_display = serializers.CharField(
        source='get_txn_type_display', read_only=True,
        help_text="Human-readable transaction type label."
    )

    class Meta:
        model  = Transaction
        fields = [
            'id', 'txn_type', 'txn_type_display', 'amount',
            'description', 'reference', 'balance_after', 'created_at',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------

class WalletSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model  = Wallet
        fields = [
            'id', 'balance', 'total_earned', 'total_withdrawn',
            'currency', 'updated_at', 'transactions',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# WithdrawalRequest
# ---------------------------------------------------------------------------

class WithdrawalRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='get_status_display', read_only=True,
        help_text="Human-readable withdrawal status label."
    )

    class Meta:
        model  = WithdrawalRequest
        fields = [
            'id', 'amount', 'status', 'status_display',
            'utr_number', 'failure_reason', 'requested_at', 'processed_at',
        ]
        read_only_fields = [
            'id', 'status', 'utr_number', 'failure_reason',
            'requested_at', 'processed_at',
        ]
        extra_kwargs = {
            'amount': {
                'help_text': 'Amount to withdraw in INR. Must be greater than zero and not exceed the current wallet balance.'
            },
        }

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Withdrawal amount must be greater than zero.')
        return value


# ---------------------------------------------------------------------------
# DriverLocation
# ---------------------------------------------------------------------------

class DriverLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DriverLocation
        fields = ['latitude', 'longitude', 'heading', 'speed', 'updated_at']
        read_only_fields = ['updated_at']
        extra_kwargs = {
            'latitude':  {'help_text': 'GPS latitude (decimal degrees, e.g. 19.076090).'},
            'longitude': {'help_text': 'GPS longitude (decimal degrees, e.g. 72.877426).'},
            'heading':   {'help_text': 'Compass bearing in degrees (0–360). Optional.'},
            'speed':     {'help_text': 'Current speed in km/h. Optional.'},
        }


# ---------------------------------------------------------------------------
# Earnings
# ---------------------------------------------------------------------------

class EarningsBreakdownSerializer(serializers.Serializer):
    """Read-only computed response — not bound to a model."""
    period           = serializers.CharField(help_text="Reporting period: 'weekly' or 'monthly'.")
    total_earned     = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Total amount earned in the period (INR).")
    total_rides      = serializers.IntegerField(help_text="Number of rides completed in the period.")
    average_per_ride = serializers.DecimalField(max_digits=10, decimal_places=2, help_text="Average earning per ride (INR).")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class DriverStatsSerializer(serializers.Serializer):
    total_rides     = serializers.IntegerField(help_text="Total number of rides completed by the driver.")
    acceptance_rate = serializers.FloatField(help_text="Ride acceptance rate as a float 0–100.")
    rating          = serializers.DecimalField(max_digits=3, decimal_places=2, help_text="Average driver rating (0.00–5.00).")
    is_verified     = serializers.BooleanField(help_text="Whether the driver's KYC and documents have been verified.")
    status          = serializers.CharField(help_text=f"Current driver status. One of: {', '.join(DriverStatus.values)}.")


# ---------------------------------------------------------------------------
# Trip History  (lightweight ride stub — replace with rides.Ride FK later)
# ---------------------------------------------------------------------------

class TripHistorySerializer(serializers.Serializer):
    """
    Placeholder shape — replace with rides.RideSerializer once the Rides app
    is implemented. Right now it queries Transaction(CREDIT) entries as a proxy.
    """
    id          = serializers.IntegerField(help_text="Transaction ID.")
    date        = serializers.DateTimeField(help_text="Date and time of the trip.")
    amount      = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Fare amount earned (INR).")
    description = serializers.CharField(help_text="Short description of the transaction.")
    reference   = serializers.CharField(help_text="Reference ID (e.g. ride ID).")


# ---------------------------------------------------------------------------
# Incentive
# ---------------------------------------------------------------------------

class IncentiveSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Incentive
        fields = [
            'id', 'title', 'description', 'target_rides',
            'bonus_amount', 'is_active', 'start_date', 'end_date',
        ]
        read_only_fields = fields


class DriverIncentiveProgressSerializer(serializers.ModelSerializer):
    incentive        = IncentiveSerializer(read_only=True)
    progress_percent = serializers.FloatField(read_only=True, help_text="Percentage progress toward the incentive target (0–100).")

    class Meta:
        model  = DriverIncentiveProgress
        fields = [
            'id', 'incentive', 'rides_completed',
            'progress_percent', 'is_claimed', 'claimed_at',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Driver Status toggle
# ---------------------------------------------------------------------------

class DriverStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[DriverStatus.ONLINE, DriverStatus.OFFLINE],
        help_text="New status for the driver. Must be 'ONLINE' or 'OFFLINE'.",
    )
