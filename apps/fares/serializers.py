from rest_framework import serializers #To Drf Serializers Classes
from.models import Fare #import fare model here . = recently edited file

class FareSerializer(serializers.ModelSerializer): #Create a serilizer class based on Faremodel
    class Meta:
        model = Fare
        fields = "__all__"  #all fields of fare

class FareCalculateSerializer(serializers.Serializer):
    ride_type = serializers.CharField()
    distance = serializers.FloatField()
    duration = serializers.FloatField()
