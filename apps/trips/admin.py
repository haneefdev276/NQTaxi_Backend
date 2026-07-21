from django.contrib import admin

from .models import Trip


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display  = [
        'id', 'rider', 'driver', 'status',
        'pickup_address', 'drop_address',
        'fare', 'distance_km', 'requested_at',
    ]
    list_filter   = ['status', 'cancelled_by', 'requested_at']
    search_fields = ['rider__username', 'driver__username', 'pickup_address', 'drop_address']
    readonly_fields = [
        'id', 'requested_at', 'accepted_at', 'started_at',
        'completed_at', 'cancelled_at', 'created_at', 'updated_at',
    ]
    ordering = ['-requested_at']

    fieldsets = (
        ('Participants', {
            'fields': ('rider', 'driver'),
        }),
        ('Locations', {
            'fields': (
                ('pickup_address', 'pickup_latitude', 'pickup_longitude'),
                ('drop_address',   'drop_latitude',   'drop_longitude'),
            ),
        }),
        ('Fare & Distance', {
            'fields': ('fare', 'distance_km'),
        }),
        ('Status & Timestamps', {
            'fields': (
                'status', 'otp',
                'requested_at', 'accepted_at', 'started_at',
                'completed_at', 'cancelled_at',
            ),
        }),
        ('Cancellation', {
            'fields': ('cancelled_by', 'cancellation_reason'),
            'classes': ('collapse',),
        }),
        ('Meta', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
