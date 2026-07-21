"""
Views for the trips app.

All business logic (state transitions, side-effects) lives in:
    apps/trips/state_machine.py  ←  TripStateMachine

Views here are thin: authenticate → fetch trip → call state machine → return response.

Endpoint mapping
────────────────────────────────────────────────────────────────────────────
POST   /api/v1/rides/request/              → TripRequestView        (Rider)
GET    /api/v1/rides/                      → TripListView           (Rider | Driver)
GET    /api/v1/rides/active/               → ActiveTripView         (Rider | Driver)
GET    /api/v1/rides/nearby-drivers/       → NearbyDriversView      (Rider)
GET    /api/v1/rides/<id>/                 → TripDetailView         (Rider | Driver)
POST   /api/v1/rides/<id>/accept/          → TripAcceptView         (Driver)
POST   /api/v1/rides/<id>/reject/          → TripRejectView         (Driver)
POST   /api/v1/rides/<id>/start/           → TripStartView          (Driver)
POST   /api/v1/rides/<id>/complete/        → TripCompleteView       (Driver)
POST   /api/v1/rides/<id>/cancel/          → TripCancelView         (Rider | Driver)
"""

import math

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter, OpenApiResponse, OpenApiExample,
    inline_serializer,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers as drf_serializers

from .models import Trip
from .serializers import (
    TripCreateSerializer,
    TripListSerializer,
    TripDetailSerializer,
    TripCancelSerializer,
    TripCompleteSerializer,
    NearbyDriverSerializer,
)
from .permissions import IsRider, IsDriverUser, IsRiderOrDriver
from .state_machine import TripStateMachine, TripTransitionError

from apps.drivers.models import DriverLocation, DriverStatus


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in km using the Haversine formula."""
    R = 6371.0
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlam = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _sm_error_response(exc: TripTransitionError) -> Response:
    """Convert a TripTransitionError into a DRF Response."""
    http_status_map = {
        400: status.HTTP_400_BAD_REQUEST,
        403: status.HTTP_403_FORBIDDEN,
        409: status.HTTP_409_CONFLICT,
    }
    return Response(
        {'detail': exc.message},
        status=http_status_map.get(exc.code, status.HTTP_409_CONFLICT),
    )


class TripPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ─────────────────────────────────────────────────────────────────────────────
# POST /rides/request/
# ─────────────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=['Trips'],
    summary='Request a new trip',
    description=(
        'A rider submits pickup and drop-off coordinates to request a trip. '
        'Returns 400 if the rider already has an active trip. '
        'A 6-digit OTP is auto-generated and returned — the rider shows it to '
        'the driver when the car arrives so the driver can start the trip.'
    ),
    request=TripCreateSerializer,
    responses={
        201: TripDetailSerializer,
        400: OpenApiResponse(description='Validation error or active trip already exists.'),
        403: OpenApiResponse(description='Rider profile required.'),
    },
    examples=[
        OpenApiExample(
            'Request a trip',
            value={
                'pickup_address':   '1 MG Road, Bangalore',
                'pickup_latitude':  '12.975109',
                'pickup_longitude': '77.607437',
                'drop_address':     'Indiranagar, Bangalore',
                'drop_latitude':    '12.978728',
                'drop_longitude':   '77.638962',
            },
            request_only=True,
        ),
    ],
)
class TripRequestView(APIView):
    """POST /rides/request/ — rider creates a new trip request."""
    permission_classes = [IsRider]

    def post(self, request):
        serializer = TripCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        trip = serializer.save()
        trip.generate_otp()
        return Response(TripDetailSerializer(trip).data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# GET /rides/
# ─────────────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=['Trips'],
    summary='List my trips',
    description=(
        'Returns a paginated list of trips for the authenticated user. '
        'Riders see trips they requested; drivers see trips they accepted/completed. '
        'Filter by status using the `status` query parameter.'
    ),
    parameters=[
        OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY,
                         description='Filter by status: REQUESTED, ACCEPTED, ONGOING, COMPLETED, CANCELLED.',
                         required=False),
        OpenApiParameter('page',      OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        OpenApiParameter('page_size', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
    ],
    responses={200: TripListSerializer(many=True)},
)
class TripListView(APIView):
    """GET /rides/ — paginated trip list for the authenticated user."""
    permission_classes = [IsRiderOrDriver]

    def get(self, request):
        user = request.user
        qs = (
            Trip.objects.filter(rider=user)
            if hasattr(user, 'rider_profile')
            else Trip.objects.filter(driver=user)
        )

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        paginator = TripPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(TripListSerializer(page, many=True).data)


# ─────────────────────────────────────────────────────────────────────────────
# GET /rides/<id>/
# ─────────────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=['Trips'],
    summary='Get trip detail',
    description='Returns full details of a specific trip. Only the rider or assigned driver can view it.',
    responses={
        200: TripDetailSerializer,
        403: OpenApiResponse(description='Not authorised to view this trip.'),
        404: OpenApiResponse(description='Trip not found.'),
    },
)
class TripDetailView(APIView):
    """GET /rides/<id>/ — retrieve a single trip."""
    permission_classes = [IsRiderOrDriver]

    def get(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        user = request.user

        if trip.rider != user and trip.driver != user:
            return Response(
                {'detail': 'You do not have permission to view this trip.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(TripDetailSerializer(trip).data)


# ─────────────────────────────────────────────────────────────────────────────
# GET /rides/active/
# ─────────────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=['Trips'],
    summary='Get active trip',
    description=(
        'Returns the current active trip (REQUESTED, ACCEPTED, or ONGOING) for the '
        'authenticated user. Returns 204 if there is no active trip.'
    ),
    responses={
        200: TripDetailSerializer,
        204: OpenApiResponse(description='No active trip.'),
    },
)
class ActiveTripView(APIView):
    """GET /rides/active/ — current in-progress trip or 204."""
    permission_classes = [IsRiderOrDriver]

    def get(self, request):
        user = request.user
        active_statuses = [Trip.Status.REQUESTED, Trip.Status.ACCEPTED, Trip.Status.ONGOING]

        qs = (
            Trip.objects.filter(rider=user, status__in=active_statuses)
            if hasattr(user, 'rider_profile')
            else Trip.objects.filter(driver=user, status__in=active_statuses)
        )
        trip = qs.first()

        if trip is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(TripDetailSerializer(trip).data)


# ─────────────────────────────────────────────────────────────────────────────
# POST /rides/<id>/accept/
# ─────────────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=['Trips'],
    summary='Accept a trip',
    description=(
        'Driver accepts a REQUESTED trip. '
        'The trip moves to ACCEPTED and the driver is linked. '
        'Returns 409 if the trip is no longer in REQUESTED state '
        '(e.g. another driver accepted it first).'
    ),
    responses={
        200: TripDetailSerializer,
        403: OpenApiResponse(description='Driver profile required.'),
        404: OpenApiResponse(description='Trip not found.'),
        409: OpenApiResponse(description='Trip is not in REQUESTED state.'),
    },
)
class TripAcceptView(APIView):
    """POST /rides/<id>/accept/ — driver accepts a requested trip."""
    permission_classes = [IsDriverUser]

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        try:
            trip = TripStateMachine(trip).accept(by_user=request.user)
        except TripTransitionError as exc:
            return _sm_error_response(exc)
        return Response(TripDetailSerializer(trip).data)


# ─────────────────────────────────────────────────────────────────────────────
# POST /rides/<id>/reject/
# ─────────────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=['Trips'],
    summary='Reject a trip',
    description=(
        'Driver rejects a REQUESTED trip. The trip stays REQUESTED so another '
        'driver can pick it up. The driver\'s rejected_rides counter is incremented.'
    ),
    responses={
        200: inline_serializer(
            name='TripRejectResponse',
            fields={'detail': drf_serializers.CharField()},
        ),
        403: OpenApiResponse(description='Driver profile required.'),
        404: OpenApiResponse(description='Trip not found.'),
        409: OpenApiResponse(description='Trip is not in REQUESTED state.'),
    },
)
class TripRejectView(APIView):
    """POST /rides/<id>/reject/ — driver rejects a requested trip."""
    permission_classes = [IsDriverUser]

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        try:
            result = TripStateMachine(trip).reject(by_user=request.user)
        except TripTransitionError as exc:
            return _sm_error_response(exc)
        return Response(result)


# ─────────────────────────────────────────────────────────────────────────────
# POST /rides/<id>/start/
# ─────────────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=['Trips'],
    summary='Start a trip',
    description=(
        'Driver marks an ACCEPTED trip as ONGOING. '
        'The driver must provide the 6-digit OTP that the rider sees on their screen. '
        'This prevents drivers from starting trips without picking up the correct rider.'
    ),
    request=inline_serializer(
        name='TripStartRequest',
        fields={'otp': drf_serializers.CharField(help_text='6-digit OTP shown to the rider.')},
    ),
    responses={
        200: TripDetailSerializer,
        400: OpenApiResponse(description='Invalid or missing OTP.'),
        403: OpenApiResponse(description='Only the assigned driver can start this trip.'),
        404: OpenApiResponse(description='Trip not found.'),
        409: OpenApiResponse(description='Trip is not in ACCEPTED state.'),
    },
    examples=[
        OpenApiExample('Start trip with OTP', value={'otp': '482931'}, request_only=True),
    ],
)
class TripStartView(APIView):
    """POST /rides/<id>/start/ — driver starts trip after OTP verification."""
    permission_classes = [IsDriverUser]

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        otp  = request.data.get('otp', '')
        try:
            trip = TripStateMachine(trip).start(by_user=request.user, otp=otp)
        except TripTransitionError as exc:
            return _sm_error_response(exc)
        return Response(TripDetailSerializer(trip).data)


# ─────────────────────────────────────────────────────────────────────────────
# POST /rides/<id>/complete/
# ─────────────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=['Trips'],
    summary='Complete a trip',
    description=(
        'Driver marks an ONGOING trip as COMPLETED. '
        'Optionally submits the final fare and distance. '
        'The driver\'s wallet is credited with the fare and all stats are updated.'
    ),
    request=TripCompleteSerializer,
    responses={
        200: TripDetailSerializer,
        403: OpenApiResponse(description='Only the assigned driver can complete this trip.'),
        404: OpenApiResponse(description='Trip not found.'),
        409: OpenApiResponse(description='Trip is not in ONGOING state.'),
    },
    examples=[
        OpenApiExample(
            'Complete trip',
            value={'fare': '185.50', 'distance_km': '8.2'},
            request_only=True,
        ),
    ],
)
class TripCompleteView(APIView):
    """POST /rides/<id>/complete/ — driver completes trip and gets credited."""
    permission_classes = [IsDriverUser]

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        serializer = TripCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            trip = TripStateMachine(trip).complete(
                by_user=request.user,
                fare=serializer.validated_data.get('fare'),
                distance_km=serializer.validated_data.get('distance_km'),
            )
        except TripTransitionError as exc:
            return _sm_error_response(exc)
        return Response(TripDetailSerializer(trip).data)


# ─────────────────────────────────────────────────────────────────────────────
# POST /rides/<id>/cancel/
# ─────────────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=['Trips'],
    summary='Cancel a trip',
    description=(
        'Either the rider or the assigned driver can cancel a trip that is in '
        'REQUESTED, ACCEPTED, or ONGOING state. An optional reason can be provided.'
    ),
    request=TripCancelSerializer,
    responses={
        200: TripDetailSerializer,
        403: OpenApiResponse(description='Not authorised to cancel this trip.'),
        404: OpenApiResponse(description='Trip not found.'),
        409: OpenApiResponse(description='Trip cannot be cancelled in its current state.'),
    },
    examples=[
        OpenApiExample(
            'Cancel with reason',
            value={'reason': 'Driver is taking too long.'},
            request_only=True,
        ),
    ],
)
class TripCancelView(APIView):
    """POST /rides/<id>/cancel/ — rider or assigned driver cancels the trip."""
    permission_classes = [IsRiderOrDriver]

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        serializer = TripCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            trip = TripStateMachine(trip).cancel(
                by_user=request.user,
                reason=serializer.validated_data.get('reason', ''),
            )
        except TripTransitionError as exc:
            return _sm_error_response(exc)
        return Response(TripDetailSerializer(trip).data)


# ─────────────────────────────────────────────────────────────────────────────
# GET /rides/nearby-drivers/
# ─────────────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=['Trips'],
    summary='Find nearby online drivers',
    description=(
        'Returns a list of currently ONLINE drivers sorted by distance from the '
        'given pickup coordinates. Limit defaults to 10 (max 50).'
    ),
    parameters=[
        OpenApiParameter('latitude',  OpenApiTypes.DECIMAL, OpenApiParameter.QUERY,
                         required=True,  description='Pickup latitude.'),
        OpenApiParameter('longitude', OpenApiTypes.DECIMAL, OpenApiParameter.QUERY,
                         required=True,  description='Pickup longitude.'),
        OpenApiParameter('limit',     OpenApiTypes.INT,     OpenApiParameter.QUERY,
                         required=False, description='Max drivers to return (default 10, max 50).'),
    ],
    responses={
        200: NearbyDriverSerializer(many=True),
        400: OpenApiResponse(description='latitude and longitude are required.'),
        403: OpenApiResponse(description='Rider profile required.'),
    },
)
class NearbyDriversView(APIView):
    """GET /rides/nearby-drivers/ — returns nearby ONLINE drivers sorted by distance."""
    permission_classes = [IsRider]

    def get(self, request):
        lat_str = request.query_params.get('latitude')
        lon_str = request.query_params.get('longitude')

        if not lat_str or not lon_str:
            return Response(
                {'detail': 'Both latitude and longitude query parameters are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            lat, lon = float(lat_str), float(lon_str)
        except ValueError:
            return Response(
                {'detail': 'latitude and longitude must be valid numbers.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit = min(int(request.query_params.get('limit', 10)), 50)

        online_locations = (
            DriverLocation.objects
            .select_related('driver', 'driver__user', 'driver__vehicle')
            .filter(driver__status=DriverStatus.ONLINE)
        )

        results = []
        for loc in online_locations:
            dist = _haversine_km(lat, lon, float(loc.latitude), float(loc.longitude))
            try:
                vehicle = loc.driver.vehicle
            except Exception:
                vehicle = None

            results.append({
                'driver_id':    loc.driver.pk,
                'name':         loc.driver.user.get_full_name() or loc.driver.user.username,
                'vehicle_type': vehicle.vehicle_type  if vehicle else 'N/A',
                'plate_number': vehicle.plate_number  if vehicle else 'N/A',
                'rating':       loc.driver.rating,
                'latitude':     loc.latitude,
                'longitude':    loc.longitude,
                'distance_km':  round(dist, 2),
            })

        results.sort(key=lambda d: d['distance_km'])
        return Response(NearbyDriverSerializer(results[:limit], many=True).data)
