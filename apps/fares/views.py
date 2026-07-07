import uuid
from decimal import Decimal
from rest_framework import generics #one of the readymade APIclasss 
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Fare
from .serializers import FareSerializer, FareCalculateSerializer

@api_view(['GET']) #tells the drf treat this function as API enpoint

def fare_detail(request, type):
    fare = get_object_or_404(Fare, ride_type=type)
    serializer = FareSerializer(fare)
    ride_id = f"RIDE_{uuid.uuid4().hex[:12].upper()}"
    return Response({
        "status" : "success",
        "message": "Fare details fetched successfully",
        "data": {"ride_id":ride_id,"ride_type": serializer.data["ride_type"],
                 "base_fare":serializer.data["base_fare"],
                 "per_km_fare":serializer.data["per_km_fare"],
                 "per_minute_rate":serializer.data["per_minute_rate"]
        }


    })

class FareListView(generics.ListAPIView):
    queryset = Fare.objects.all()
    serializer_class = FareSerializer

    def list(self, request, *args, **kwargs):
        fares = self.get_queryset()
        serializer = self.get_serializer(fares, many=True)

        data = []

        for fare in serializer.data:
            ride_id = f"RIDE_{uuid.uuid4().hex[:12].upper()}"

            data.append({
                "ride_id": ride_id,
                "ride_type": fare["ride_type"],
                "base_fare": fare["base_fare"],
                "per_km_fare": fare["per_km_fare"],
                "per_minute_rate": fare["per_minute_rate"]
            })

        return Response({
            "status": "success",
            "message": "Fare details fetched successfully",
            "data": data
        })


@extend_schema(
    request=FareCalculateSerializer,
    responses={
        200: None
    }
)
@api_view(['POST'])
def calculate_fare(request):
    serializer = FareCalculateSerializer(data=request.data)
    if serializer.is_valid():
        ride_type = serializer.validated_data["ride_type"]
        distance = serializer.validated_data["distance"]
        duration = serializer.validated_data["duration"]
    else:
        fare_id = f"FARE_{uuid.uuid4().hex[:12].upper()}"
        return Response({"status" : "success",
        "message": "Fare details fetched successfully",
       "data":{
           "fare_id": fare_id,
            "ride_type": ride_type,
            "distance": distance,
            "duration": duration,
            "base_fare": str(fare.base),
            "per_km_fare":str(fare.per_minute),
            "per_minute_rate":str(fare.per_minute_rate),
            "total_fare" :str(total_fare)
           
       } 

        })

    fare = get_object_or_404(Fare,ride_type=ride_type)#it will get the fare from the database based on the ride type

    base_fare = fare.base_fare
    distance_fare = Decimal(distance) * fare.per_km_fare
    duration_fare = Decimal(duration)* fare.per_minute_rate
    total_fare = base_fare + distance_fare + duration_fare 

    fare_id = f"FARE_{uuid.uuid4().hex[:12].upper()}"
    return Response({ 
        "status" : "success",
        "message": "Fare details fetched successfully",
        "data":{
            "fare_id": fare_id,
            "ride_type": ride_type,
            "distance": distance,
            "duration": duration,
            "total_fare" :str(total_fare)
        }

    })
        
