"""
Admin registrations for the drivers app.
"""

from django.contrib import admin
from .models import (
    DriverProfile, Vehicle, Document, BankDetails,
    Wallet, Transaction, WithdrawalRequest,
    DriverLocation, Incentive, DriverIncentiveProgress,
)


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'phone', 'status', 'rating', 'total_rides', 'is_verified', 'created_at']
    list_filter   = ['status', 'is_verified', 'city']
    search_fields = ['user__username', 'user__email', 'phone', 'licence_number']
    readonly_fields = ['created_at', 'updated_at', 'acceptance_rate']

    @admin.display(description='Acceptance Rate (%)')
    def acceptance_rate(self, obj):
        return obj.acceptance_rate


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display  = ['driver', 'make', 'model', 'year', 'plate_number', 'vehicle_type', 'is_verified']
    list_filter   = ['vehicle_type', 'is_verified']
    search_fields = ['plate_number', 'driver__user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display  = ['driver', 'doc_type', 'status', 'uploaded_at', 'reviewed_at']
    list_filter   = ['doc_type', 'status']
    search_fields = ['driver__user__username', 's3_key']
    readonly_fields = ['uploaded_at', 'reviewed_at']


@admin.register(BankDetails)
class BankDetailsAdmin(admin.ModelAdmin):
    list_display  = ['driver', 'bank_name', 'account_holder', 'ifsc_code', 'is_verified']
    list_filter   = ['is_verified', 'bank_name']
    search_fields = ['driver__user__username', 'account_number', 'ifsc_code']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display    = ['driver', 'balance', 'total_earned', 'total_withdrawn', 'currency', 'updated_at']
    readonly_fields = ['updated_at']
    search_fields   = ['driver__user__username']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display    = ['wallet', 'txn_type', 'amount', 'balance_after', 'description', 'created_at']
    list_filter     = ['txn_type']
    search_fields   = ['wallet__driver__user__username', 'reference']
    readonly_fields = ['created_at']


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display    = ['driver', 'amount', 'status', 'requested_at', 'processed_at']
    list_filter     = ['status']
    search_fields   = ['driver__user__username', 'utr_number']
    readonly_fields = ['requested_at', 'processed_at']


@admin.register(DriverLocation)
class DriverLocationAdmin(admin.ModelAdmin):
    list_display    = ['driver', 'latitude', 'longitude', 'speed', 'updated_at']
    search_fields   = ['driver__user__username']
    readonly_fields = ['updated_at']


@admin.register(Incentive)
class IncentiveAdmin(admin.ModelAdmin):
    list_display  = ['title', 'target_rides', 'bonus_amount', 'is_active', 'start_date', 'end_date']
    list_filter   = ['is_active']
    search_fields = ['title']


@admin.register(DriverIncentiveProgress)
class DriverIncentiveProgressAdmin(admin.ModelAdmin):
    list_display  = ['driver', 'incentive', 'rides_completed', 'is_claimed', 'claimed_at']
    list_filter   = ['is_claimed', 'incentive']
    search_fields = ['driver__user__username']
    readonly_fields = ['claimed_at']
