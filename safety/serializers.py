from rest_framework import serializers
from .models import SOSAlert


class SOSAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = SOSAlert
        fields = '__all__'
        read_only_fields = (
            'id',
            'user',
            'status',
            'created_at',
            'resolved_at',
        )