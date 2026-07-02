from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.customers.models import RiderProfile
from apps.users.models import UserProfile

User = get_user_model()


def get_public_user_id(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return str(profile.uuid)


class UserPublicSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email')

    def get_id(self, obj):
        return get_public_user_id(obj)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
        UserProfile.objects.create(user=user)
        RiderProfile.objects.get_or_create(user=user)
        from apps.notifications.utils import ensure_welcome_notification

        ensure_welcome_notification(user)
        return user
