from rest_framework import serializers

from apps.notifications.models import FCMDeviceToken, Notification


class EmptyBodySerializer(serializers.Serializer):
    """OpenAPI placeholder for action endpoints that accept an empty JSON body."""


class NotificationReadAllRequestSerializer(serializers.Serializer):
    confirm = serializers.BooleanField(
        required=False,
        default=True,
        help_text='Optional. Send true (or omit) to mark all notifications as read.',
    )


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            'id',
            'title',
            'body',
            'notification_type',
            'is_read',
            'read_at',
            'data',
            'created_at',
        )
        read_only_fields = fields


class NotificationMarkReadResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    notification = NotificationSerializer()


class NotificationReadAllResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    updated_count = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    total_count = serializers.IntegerField()


class NotificationErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    error = serializers.CharField()
    code = serializers.CharField()


class NotificationListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    notifications = NotificationSerializer(many=True)
    unread_count = serializers.IntegerField()
    count = serializers.IntegerField(required=False)
    next = serializers.URLField(allow_null=True, required=False)
    previous = serializers.URLField(allow_null=True, required=False)


class FCMTokenRegisterSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)
    device_type = serializers.ChoiceField(
        choices=[FCMDeviceToken.DEVICE_ANDROID, FCMDeviceToken.DEVICE_IOS],
        required=False,
        allow_blank=True,
    )

    def create(self, validated_data):
        user = self.context['request'].user
        token = validated_data['token']
        device_type = validated_data.get('device_type', '')

        device_token, _created = FCMDeviceToken.objects.update_or_create(
            token=token,
            defaults={
                'user': user,
                'device_type': device_type,
                'is_active': True,
            },
        )
        return device_token


class FCMDeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDeviceToken
        fields = ('id', 'token', 'device_type', 'is_active', 'created_at', 'updated_at')
        read_only_fields = fields


class FCMTokenRegisterResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    fcm_token = FCMDeviceTokenSerializer()
