from decimal import Decimal

from django.conf import settings
from django.apps import apps
from rest_framework import serializers

from apps.customers.models import EmergencyContact, PaymentMethod, RiderProfile, SavedPlace, WalletTransaction
from apps.customers.utils import get_rider_profile
from apps.core.utils import paise_to_rupees


class RiderProfileSerializer(serializers.ModelSerializer):
    wallet_balance_rupees = serializers.SerializerMethodField(read_only=True)
    user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RiderProfile
        fields = (
            'id', 'user', 'rating', 'total_rides', 'wallet_balance_rupees',
            'home_address', 'work_address', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'user', 'rating', 'total_rides', 'wallet_balance_rupees',
            'created_at', 'updated_at'
        )

    def get_wallet_balance_rupees(self, obj):
        return paise_to_rupees(obj.wallet_balance)

    def get_user(self, obj):
        from apps.users.serializers import UserPublicSerializer

        return UserPublicSerializer(obj.user).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('rating') is not None:
            data['rating'] = float(data['rating'])
        return data


class RiderProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiderProfile
        fields = ('home_address', 'work_address')
        extra_kwargs = {
            'home_address': {'required': False, 'allow_null': True, 'allow_blank': True},
            'work_address': {'required': False, 'allow_null': True, 'allow_blank': True},
        }

    def validate_home_address(self, value):
        if value is None:
            return value
        value = value.strip()
        return value or None

    def validate_work_address(self, value):
        if value is None:
            return value
        value = value.strip()
        return value or None

    def validate(self, attrs):
        if not self.partial and not attrs:
            raise serializers.ValidationError('At least one of home_address or work_address is required.')
        return attrs


class PaymentMethodSerializer(serializers.ModelSerializer):
    payment_gateway_token = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = PaymentMethod
        fields = (
            'id', 'type', 'card_last4', 'card_brand', 'card_expiry', 'card_holder',
            'upi_id', 'upi_name', 'is_default', 'created_at', 'payment_gateway_token'
        )
        read_only_fields = ('id', 'created_at')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.type == 'card':
            data.pop('upi_id', None)
            data.pop('upi_name', None)
        elif instance.type == 'upi':
            data.pop('card_last4', None)
            data.pop('card_brand', None)
            data.pop('card_expiry', None)
            data.pop('card_holder', None)
        return data

    def validate(self, attrs):
        if 'card_number' in self.initial_data or 'cvv' in self.initial_data:
            raise serializers.ValidationError({
                'non_field_errors': ['Raw card details are not accepted. Use a secure payment gateway token instead.']
            })

        payment_type = attrs.get('type')
        if payment_type == 'card':
            if not attrs.get('card_last4') or not attrs.get('card_expiry'):
                raise serializers.ValidationError({
                    'card_last4': 'This field is required for card payments.',
                    'card_expiry': 'This field is required for card payments.'
                })
        if payment_type == 'upi':
            if not attrs.get('upi_id'):
                raise serializers.ValidationError({'upi_id': 'This field is required for UPI payments.'})

        request = self.context.get('request')
        if request and getattr(request.user, 'is_authenticated', False):
            rider = get_rider_profile(request.user)
            if payment_type == 'card':
                card_last4 = attrs.get('card_last4')
                card_expiry = attrs.get('card_expiry')
                if card_last4 and card_expiry:
                    queryset = PaymentMethod.objects.filter(
                        rider=rider,
                        type='card',
                        card_last4=card_last4,
                        card_expiry=card_expiry,
                    )
                    if self.instance is not None:
                        queryset = queryset.exclude(pk=self.instance.pk)
                    if queryset.exists():
                        raise serializers.ValidationError({
                            'card_last4': 'This card is already saved.',
                        })
            if payment_type == 'upi':
                upi_id = attrs.get('upi_id')
                if upi_id:
                    queryset = PaymentMethod.objects.filter(rider=rider, type='upi', upi_id=upi_id)
                    if self.instance is not None:
                        queryset = queryset.exclude(pk=self.instance.pk)
                    if queryset.exists():
                        raise serializers.ValidationError({
                            'upi_id': 'This UPI ID is already saved.',
                        })

        token = attrs.pop('payment_gateway_token', None)
        if token:
            attrs['razorpay_token'] = token
        return attrs


class SavedPlaceSerializer(serializers.ModelSerializer):
    label = serializers.CharField(max_length=20)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8, coerce_to_string=False)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8, coerce_to_string=False)

    class Meta:
        model = SavedPlace
        fields = ('id', 'label', 'name', 'address', 'latitude', 'longitude', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_label(self, value):
        normalized = value.strip().lower()
        if not normalized:
            raise serializers.ValidationError('Label is required.')
        if len(normalized) > 20:
            raise serializers.ValidationError('Label must be at most 20 characters.')
        return normalized

    def validate(self, attrs):
        request = self.context.get('request')
        if request and getattr(request.user, 'is_authenticated', False):
            rider = get_rider_profile(request.user)
            label = attrs.get('label')
            if label in ('home', 'work'):
                queryset = SavedPlace.objects.filter(rider=rider, label=label)
                if self.instance is not None:
                    queryset = queryset.exclude(pk=self.instance.pk)
                if queryset.exists():
                    raise serializers.ValidationError({
                        'label': f'You already have a saved place labelled "{label}".',
                    })
        return attrs


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ('id', 'name', 'phone', 'relationship', 'is_primary', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_phone(self, value):
        phone = value.strip()
        if not phone:
            raise serializers.ValidationError('Phone number is required.')
        if len(phone) > 15:
            raise serializers.ValidationError('Phone number must be at most 15 characters.')
        return phone

    def validate(self, attrs):
        request = self.context.get('request')
        if request and getattr(request.user, 'is_authenticated', False):
            rider = get_rider_profile(request.user)
            phone = attrs.get('phone')
            if phone:
                queryset = EmergencyContact.objects.filter(rider=rider, phone=phone.strip())
                if self.instance is not None:
                    queryset = queryset.exclude(pk=self.instance.pk)
                if queryset.exists():
                    raise serializers.ValidationError({
                        'phone': 'An emergency contact with this phone number already exists.',
                    })
        return attrs


class WalletSerializer(serializers.Serializer):
    balance_rupees = serializers.SerializerMethodField()
    transactions = serializers.ListField(child=serializers.DictField(), required=False)

    def get_balance_rupees(self, obj):
        return round(float(obj.wallet_balance) / 100, 2)


class WalletTransactionSerializer(serializers.ModelSerializer):
    amount_rupees = serializers.SerializerMethodField()

    class Meta:
        model = WalletTransaction
        fields = ('id', 'type', 'amount_rupees', 'description', 'status', 'created_at')
        read_only_fields = fields

    def get_amount_rupees(self, obj):
        return paise_to_rupees(obj.amount)


class WalletTopupSerializer(serializers.Serializer):
    amount_rupees = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('10.00'),
        max_value=Decimal('50000.00'),
    )

    def validate_amount_rupees(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be a positive value.')
        return value


class WalletTopupDevConfirmSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField(max_length=100)


class WalletTopupVerifySerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField(max_length=100)
    razorpay_payment_id = serializers.CharField(max_length=100)
    razorpay_signature = serializers.CharField(max_length=255)


class TripHistorySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    pickup_address = serializers.CharField(read_only=True)
    drop_address = serializers.CharField(read_only=True)
    fare_rupees = serializers.FloatField(read_only=True)
    status = serializers.CharField(read_only=True)
    driver_name = serializers.CharField(read_only=True)
    requested_at = serializers.DateTimeField(read_only=True)
    started_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        driver = getattr(instance, 'driver', None)
        requested_at = getattr(instance, 'requested_at', None)
        completed_at = getattr(instance, 'completed_at', None)
        fare = getattr(instance, 'fare', None)

        return {
            'id': getattr(instance, 'id', None),
            'pickup_address': getattr(instance, 'pickup_address', ''),
            'drop_address': getattr(instance, 'drop_address', ''),
            'fare_rupees': float(fare) if fare is not None else 0.0,
            'status': str(getattr(instance, 'status', '')).lower(),
            'driver_name': getattr(driver, 'username', '') or '',
            'requested_at': requested_at,
            'started_at': getattr(instance, 'started_at', None),
            'completed_at': completed_at,
        }


class RatingSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    trip_id = serializers.UUIDField(read_only=True)
    score = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)
    comment = serializers.CharField(read_only=True)
    given_by = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        return {
            'id': getattr(instance, 'id', None),
            'trip_id': str(getattr(instance, 'trip_id', None) or ''),
            'score': float(getattr(instance, 'score', 0) or 0),
            'comment': getattr(instance, 'comment', ''),
            'given_by': getattr(getattr(instance, 'given_by_rider', None), 'username', ''),
            'created_at': getattr(instance, 'created_at', None),
        }
