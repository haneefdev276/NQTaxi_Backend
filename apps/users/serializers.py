from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import CustomerProfile
from apps.drivers.models import DriverProfile

User = get_user_model()

class BaseUserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    phone = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'email', 'first_name', 'last_name', 'phone')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

class CustomerRegistrationSerializer(BaseUserRegistrationSerializer):
    def create(self, validated_data):
        phone = validated_data.pop('phone')
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                password=validated_data['password'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name']
            )
            CustomerProfile.objects.create(user=user, phone=phone)
        return user


class DriverRegistrationSerializer(BaseUserRegistrationSerializer):
    def create(self, validated_data):
        phone = validated_data.pop('phone')
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                password=validated_data['password'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name']
            )
            DriverProfile.objects.create(user=user, phone=phone)
        return user
