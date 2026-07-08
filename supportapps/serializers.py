from rest_framework import serializers
from .models import SupportTicket, SupportMessage


class SupportTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = "__all__"
        read_only_fields = ["user"]

class SupportMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportMessage
        fields = "__all__"
        read_only_fields = ["sender","ticket"]
  
    
