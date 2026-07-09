"""
Serializers for the trips app.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Trip

User = get_user_model()


# ---------------------------------------------------------------------------
# Nested participant serializers (read-only)
# ---------------------------------------------------------------------------

class UserBriefSerializer(serializers.ModelSerializer):
    """Minimal user info for embedding in trip responses."""
    class Meta:
        model  = User
        fields = ['id', 'username', 'first_name', 'last_name', 'phone']
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Trip Create  (POST /rides/request/)
# ---------------------------------------------------------------------------

class TripCreateSerializer(serializers.ModelSerializer):
    """
    Used by a rider to request a new trip.
    The `rider` field is set automatically from request.user.
    """

    class Meta:
        model  = Trip
        fields = [
            'pickup_address',   'pickup_latitude',  'pickup_longitude',
            'drop_address',     'drop_latitude',    'drop_longitude',
        ]
        extra_kwargs = {
            'pickup_address':   {'help_text': 'Human-readable pickup address.'},
            'pickup_latitude':  {'help_text': 'Pickup latitude (decimal degrees).'},
            'pickup_longitude': {'help_text': 'Pickup longitude (decimal degrees).'},
            'drop_address':     {'help_text': 'Human-readable drop-off address.'},
            'drop_latitude':    {'help_text': 'Drop-off latitude (decimal degrees).'},
            'drop_longitude':   {'help_text': 'Drop-off longitude (decimal degrees).'},
        }

    def validate(self, attrs):
        # Prevent duplicate active requests from the same rider
        rider = self.context['request'].user
        if Trip.objects.filter(
            rider=rider,
            status__in=[Trip.Status.REQUESTED, Trip.Status.ACCEPTED, Trip.Status.ONGOING],
        ).exists():
            raise serializers.ValidationError(
                'You already have an active trip. Complete or cancel it before requesting a new one.'
            )
        return attrs

    def create(self, validated_data):
        rider = self.context['request'].user
        return Trip.objects.create(rider=rider, **validated_data)


# ---------------------------------------------------------------------------
# Trip List  (GET /rides/)
# ---------------------------------------------------------------------------

class TripListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Trip
        fields = [
            'id', 'status', 'status_display',
            'pickup_address', 'drop_address',
            'fare', 'distance_km',
            'requested_at', 'completed_at',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Trip Detail  (GET /rides/{id}/)
# ---------------------------------------------------------------------------

class TripDetailSerializer(serializers.ModelSerializer):
    """Full trip detail including nested participant info."""
    rider          = UserBriefSerializer(read_only=True)
    driver         = UserBriefSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Trip
        fields = [
            'id',
            'rider', 'driver',
            'status', 'status_display',
            'pickup_address',   'pickup_latitude',  'pickup_longitude',
            'drop_address',     'drop_latitude',    'drop_longitude',
            'fare', 'distance_km',
            'otp',
            'requested_at', 'accepted_at', 'started_at',
            'completed_at', 'cancelled_at',
            'cancelled_by', 'cancellation_reason',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Trip Cancel  (POST /rides/{id}/cancel/)
# ---------------------------------------------------------------------------

class TripCancelSerializer(serializers.Serializer):
    """Optional cancellation reason from the cancelling party."""
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text='Optional reason for cancelling the trip.',
    )


# ---------------------------------------------------------------------------
# Trip Complete  (POST /rides/{id}/complete/)
# ---------------------------------------------------------------------------

class TripCompleteSerializer(serializers.Serializer):
    """
    Driver submits the final fare and distance when completing a trip.
    Both fields are optional — the platform may compute them independently.
    """
    fare        = serializers.DecimalField(
        max_digits=8, decimal_places=2,
        required=False, allow_null=True,
        min_value=0,
        help_text='Final fare in INR. Leave blank to use pre-computed fare.',
    )
    distance_km = serializers.DecimalField(
        max_digits=6, decimal_places=2,
        required=False, allow_null=True,
        min_value=0,
        help_text='Trip distance in kilometres.',
    )


# ---------------------------------------------------------------------------
# Nearby Driver  (GET /rides/nearby-drivers/)  — read-only
# ---------------------------------------------------------------------------

class NearbyDriverSerializer(serializers.Serializer):
    """Represents a single online driver near the requested location."""
    driver_id       = serializers.UUIDField(help_text='DriverProfile UUID.')
    name            = serializers.CharField(help_text='Full name of the driver.')
    vehicle_type    = serializers.CharField(help_text='Type of vehicle (e.g. SEDAN, SUV).')
    plate_number    = serializers.CharField(help_text='Vehicle plate number.')
    rating          = serializers.DecimalField(
        max_digits=3, decimal_places=2,
        help_text='Average driver rating (0.00–5.00).',
    )
    latitude        = serializers.DecimalField(
        max_digits=9, decimal_places=6,
        help_text='Driver\'s current latitude.',
    )
    longitude       = serializers.DecimalField(
        max_digits=9, decimal_places=6,
        help_text='Driver\'s current longitude.',
    )
    distance_km     = serializers.FloatField(
        help_text='Approximate distance from the pickup point in km.',
    )
