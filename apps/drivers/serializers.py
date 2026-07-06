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
    acceptance_rate  = serializers.FloatField(read_only=True)
    status_display   = serializers.CharField(source='get_status_display', read_only=True)

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


# ---------------------------------------------------------------------------
# Vehicle
# ---------------------------------------------------------------------------

class VehicleSerializer(serializers.ModelSerializer):
    vehicle_type_display = serializers.CharField(source='get_vehicle_type_display', read_only=True)

    class Meta:
        model  = Vehicle
        fields = [
            'id', 'make', 'model', 'year', 'plate_number', 'color',
            'vehicle_type', 'vehicle_type_display', 'rc_number',
            'is_verified', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_verified', 'created_at', 'updated_at']


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

class DocumentSerializer(serializers.ModelSerializer):
    doc_type_display  = serializers.CharField(source='get_doc_type_display', read_only=True)
    status_display    = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Document
        fields = [
            'id', 'doc_type', 'doc_type_display', 's3_key', 'original_name',
            'status', 'status_display', 'rejection_reason',
            'uploaded_at', 'reviewed_at',
        ]
        read_only_fields = ['id', 'status', 'rejection_reason', 'uploaded_at', 'reviewed_at']


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Used for POST /documents/upload/ — driver registers an uploaded S3 object."""
    class Meta:
        model  = Document
        fields = ['doc_type', 's3_key', 'original_name']

    def validate_s3_key(self, value):
        if not value.strip():
            raise serializers.ValidationError('s3_key must not be blank.')
        return value.strip()


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


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class TransactionSerializer(serializers.ModelSerializer):
    txn_type_display = serializers.CharField(source='get_txn_type_display', read_only=True)

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
    status_display = serializers.CharField(source='get_status_display', read_only=True)

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


# ---------------------------------------------------------------------------
# Earnings
# ---------------------------------------------------------------------------

class EarningsBreakdownSerializer(serializers.Serializer):
    """Read-only computed response — not bound to a model."""
    period       = serializers.CharField()
    total_earned = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_rides  = serializers.IntegerField()
    average_per_ride = serializers.DecimalField(max_digits=10, decimal_places=2)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class DriverStatsSerializer(serializers.Serializer):
    total_rides     = serializers.IntegerField()
    acceptance_rate = serializers.FloatField()
    rating          = serializers.DecimalField(max_digits=3, decimal_places=2)
    is_verified     = serializers.BooleanField()
    status          = serializers.CharField()


# ---------------------------------------------------------------------------
# Trip History  (lightweight ride stub — replace with rides.Ride FK later)
# ---------------------------------------------------------------------------

class TripHistorySerializer(serializers.Serializer):
    """
    Placeholder shape — replace with rides.RideSerializer once the Rides app
    is implemented. Right now it queries Transaction(CREDIT) entries as a proxy.
    """
    id          = serializers.IntegerField()
    date        = serializers.DateTimeField()
    amount      = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField()
    reference   = serializers.CharField()


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
    incentive       = IncentiveSerializer(read_only=True)
    progress_percent = serializers.FloatField(read_only=True)

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
    status = serializers.ChoiceField(choices=['ONLINE', 'OFFLINE'])
