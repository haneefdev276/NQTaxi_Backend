"""
Views for the drivers app.

All views require JWT authentication + IsDriver permission unless otherwise noted.

Endpoint mapping
----------------
GET  /profile/              → DriverProfileView
PATCH /profile/             → DriverProfileView

GET  /vehicle/              → VehicleView
POST /vehicle/              → VehicleView
PATCH /vehicle/             → VehicleView

GET  /documents/            → DocumentListView
POST /documents/upload/     → DocumentUploadView
DELETE /documents/{id}/     → DocumentDeleteView

PATCH /status/              → DriverStatusView

GET  /wallet/               → WalletView
POST /wallet/withdraw/      → WithdrawView

GET  /bank-details/         → BankDetailsView
PATCH /bank-details/        → BankDetailsView

GET  /earnings/             → EarningsView
GET  /stats/                → StatsView
GET  /trip-history/         → TripHistoryView
GET  /incentives/           → IncentivesView
POST /location/             → LocationView
"""

from decimal import Decimal
from datetime import timedelta

from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from drf_spectacular.utils import (
    extend_schema, extend_schema_view,
    OpenApiParameter, OpenApiExample, OpenApiResponse,
    inline_serializer,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers as drf_serializers

from .models import (
    DriverProfile, Vehicle, Document, BankDetails,
    Wallet, Transaction, WithdrawalRequest,
    DriverLocation, Incentive, DriverIncentiveProgress,
    DriverStatus, TransactionType, WithdrawalStatus,
)
from .serializers import (
    DriverProfileSerializer, DriverProfileUpdateSerializer,
    VehicleSerializer,
    DocumentSerializer, DocumentUploadSerializer,
    BankDetailsSerializer,
    WalletSerializer, WithdrawalRequestSerializer,
    DriverLocationSerializer,
    DriverStatsSerializer, EarningsBreakdownSerializer,
    TripHistorySerializer,
    DriverIncentiveProgressSerializer,
    DriverStatusSerializer,
)
from .permissions import IsDriver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_driver(request) -> DriverProfile:
    """Return the DriverProfile for the authenticated user."""
    return request.user.driver_profile


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@extend_schema_view(
    get=extend_schema(
        tags=["Driver – Profile"],
        summary="Get driver profile",
        description="Returns the full profile of the currently authenticated driver.",
        responses={
            200: DriverProfileSerializer,
        },
    ),
    patch=extend_schema(
        tags=["Driver – Profile"],
        summary="Update driver profile",
        description=(
            "Partially update editable fields on the driver's profile "
            "(phone, date_of_birth, gender, profile_photo, licence_number, "
            "licence_expiry, city, state)."
        ),
        request=DriverProfileUpdateSerializer,
        responses={
            200: DriverProfileSerializer,
        },
        examples=[
            OpenApiExample(
                "Update city & phone",
                value={"phone": "+91-9876543210", "city": "Mumbai", "state": "Maharashtra"},
                request_only=True,
            ),
        ],
    ),
)
class DriverProfileView(APIView):
    """
    GET  /drivers/profile/  — return full driver profile
    PATCH /drivers/profile/ — update editable fields
    """
    permission_classes = [IsDriver]

    def get(self, request):
        driver = get_driver(request)
        serializer = DriverProfileSerializer(driver)
        return Response(serializer.data)

    def patch(self, request):
        driver = get_driver(request)
        serializer = DriverProfileUpdateSerializer(driver, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(DriverProfileSerializer(driver).data)


# ---------------------------------------------------------------------------
# Vehicle
# ---------------------------------------------------------------------------

@extend_schema_view(
    get=extend_schema(
        tags=["Driver – Vehicle"],
        summary="Get vehicle details",
        description="Returns the driver's registered vehicle. Returns 404 if no vehicle is registered yet.",
        responses={
            200: VehicleSerializer,
            404: OpenApiResponse(description="No vehicle registered yet."),
        },
    ),
    post=extend_schema(
        tags=["Driver – Vehicle"],
        summary="Register a vehicle",
        description="Create a new vehicle record for the driver. Returns 409 if a vehicle already exists — use PATCH to update.",
        request=VehicleSerializer,
        responses={
            201: VehicleSerializer,
            409: OpenApiResponse(description="Vehicle already exists. Use PATCH to update."),
        },
        examples=[
            OpenApiExample(
                "Register Sedan",
                value={
                    "make": "Maruti",
                    "model": "Swift Dzire",
                    "year": 2022,
                    "plate_number": "MH12AB1234",
                    "color": "White",
                    "vehicle_type": "SEDAN",
                    "rc_number": "MH1220220012345",
                },
                request_only=True,
            ),
        ],
    ),
    patch=extend_schema(
        tags=["Driver – Vehicle"],
        summary="Update vehicle details",
        description="Partially update the driver's existing vehicle record.",
        request=VehicleSerializer,
        responses={
            200: VehicleSerializer,
            404: OpenApiResponse(description="No vehicle registered yet."),
        },
        examples=[
            OpenApiExample(
                "Update color",
                value={"color": "Silver"},
                request_only=True,
            ),
        ],
    ),
)
class VehicleView(APIView):
    """
    GET   /drivers/vehicle/  — retrieve vehicle (404 if not set)
    POST  /drivers/vehicle/  — create vehicle (409 if already exists)
    PATCH /drivers/vehicle/  — update vehicle
    """
    permission_classes = [IsDriver]

    def _get_vehicle_or_none(self, driver):
        try:
            return driver.vehicle
        except Vehicle.DoesNotExist:
            return None

    def get(self, request):
        driver  = get_driver(request)
        vehicle = self._get_vehicle_or_none(driver)
        if vehicle is None:
            return Response({'detail': 'No vehicle registered yet.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(VehicleSerializer(vehicle).data)

    def post(self, request):
        driver  = get_driver(request)
        if self._get_vehicle_or_none(driver) is not None:
            return Response(
                {'detail': 'Vehicle already exists. Use PATCH to update.'},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = VehicleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(driver=driver)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        driver  = get_driver(request)
        vehicle = self._get_vehicle_or_none(driver)
        if vehicle is None:
            return Response({'detail': 'No vehicle registered yet.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = VehicleSerializer(vehicle, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Driver – Documents"],
    summary="List driver documents",
    description="Returns all KYC / licence documents uploaded by the authenticated driver.",
    responses={200: DocumentSerializer(many=True)},
)
class DocumentListView(APIView):
    """GET /drivers/documents/ — list all documents for the driver."""
    permission_classes = [IsDriver]

    def get(self, request):
        driver = get_driver(request)
        docs   = driver.documents.all()
        serializer = DocumentSerializer(docs, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=["Driver – Documents"],
    summary="Upload a document",
    description=(
        "Register an already-uploaded S3 document key for the driver. "
        "The file must have been uploaded to S3 beforehand; this endpoint "
        "only records the S3 key reference."
    ),
    request=DocumentUploadSerializer,
    responses={
        201: DocumentSerializer,
        400: OpenApiResponse(description="Validation error."),
    },
    examples=[
        OpenApiExample(
            "Upload driver licence",
            value={
                "doc_type": "LICENCE",
                "s3_key": "drivers/123/licence/abc123.pdf",
                "original_name": "driving_licence.pdf",
            },
            request_only=True,
        ),
    ],
)
class DocumentUploadView(APIView):
    """
    POST /drivers/documents/upload/
    Register an already-uploaded S3 document key.
    """
    permission_classes = [IsDriver]

    def post(self, request):
        driver     = get_driver(request)
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = serializer.save(driver=driver)
        return Response(DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Driver – Documents"],
    summary="Delete a document",
    description="Delete a specific document belonging to the authenticated driver.",
    responses={
        204: OpenApiResponse(description="Document deleted successfully."),
        404: OpenApiResponse(description="Document not found."),
    },
)
class DocumentDeleteView(APIView):
    """DELETE /drivers/documents/{id}/ — remove a document belonging to the driver."""
    permission_classes = [IsDriver]

    def delete(self, request, pk):
        driver = get_driver(request)
        doc    = get_object_or_404(Document, pk=pk, driver=driver)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Driver – Status"],
    summary="Toggle driver status",
    description=(
        "Set the driver's availability status to ONLINE or OFFLINE. "
        "Blocked drivers cannot change their status."
    ),
    request=DriverStatusSerializer,
    responses={
        200: inline_serializer(
            name="DriverStatusResponse",
            fields={
                "status": drf_serializers.CharField(),
                "status_display": drf_serializers.CharField(),
            },
        ),
        403: OpenApiResponse(description="Account is blocked. Contact support."),
    },
    examples=[
        OpenApiExample(
            "Go online",
            value={"status": "ONLINE"},
            request_only=True,
        ),
        OpenApiExample(
            "Go offline",
            value={"status": "OFFLINE"},
            request_only=True,
        ),
    ],
)
class DriverStatusView(APIView):
    """PATCH /drivers/status/ — toggle ONLINE / OFFLINE."""
    permission_classes = [IsDriver]

    def patch(self, request):
        driver     = get_driver(request)
        serializer = DriverStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']

        if driver.status == DriverStatus.BLOCKED:
            return Response(
                {'detail': 'Your account is blocked. Please contact support.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        driver.status = new_status
        driver.save(update_fields=['status', 'updated_at'])
        return Response({'status': driver.status, 'status_display': driver.get_status_display()})


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Driver – Wallet"],
    summary="Get wallet balance",
    description="Returns the driver's wallet balance along with the last 50 transactions.",
    responses={200: WalletSerializer},
)
class WalletView(APIView):
    """GET /drivers/wallet/ — wallet balance + last 50 transactions."""
    permission_classes = [IsDriver]

    def get(self, request):
        driver = get_driver(request)
        wallet, _ = Wallet.objects.get_or_create(driver=driver)
        # Limit transactions returned inline (most recent 50)
        wallet_data = WalletSerializer(wallet).data
        wallet_data['transactions'] = wallet_data['transactions'][:50]
        return Response(wallet_data)


# ---------------------------------------------------------------------------
# Withdraw
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Driver – Wallet"],
    summary="Request a withdrawal",
    description=(
        "Create a withdrawal request for the given amount. "
        "The amount is immediately deducted from the wallet balance. "
        "Returns 400 if the balance is insufficient."
    ),
    request=WithdrawalRequestSerializer,
    responses={
        201: WithdrawalRequestSerializer,
        400: OpenApiResponse(description="Insufficient balance or invalid amount."),
    },
    examples=[
        OpenApiExample(
            "Withdraw ₹500",
            value={"amount": "500.00"},
            request_only=True,
        ),
    ],
)
class WithdrawView(APIView):
    """POST /drivers/wallet/withdraw/ — create a withdrawal request."""
    permission_classes = [IsDriver]

    def post(self, request):
        driver = get_driver(request)
        serializer = WithdrawalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']

        wallet, _ = Wallet.objects.get_or_create(driver=driver)
        if wallet.balance < amount:
            return Response(
                {'detail': f'Insufficient balance. Available: {wallet.currency} {wallet.balance}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Deduct balance and record transaction
        wallet.balance          -= amount
        wallet.total_withdrawn  += amount
        wallet.save(update_fields=['balance', 'total_withdrawn', 'updated_at'])

        withdrawal = WithdrawalRequest.objects.create(
            driver=driver,
            amount=amount,
            status=WithdrawalStatus.PENDING,
            bank_details=getattr(driver, 'bank_details', None),
        )

        Transaction.objects.create(
            wallet=wallet,
            txn_type=TransactionType.WITHDRAWAL,
            amount=amount,
            description='Withdrawal request',
            reference=str(withdrawal.pk),
            balance_after=wallet.balance,
        )

        return Response(WithdrawalRequestSerializer(withdrawal).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Bank Details
# ---------------------------------------------------------------------------

@extend_schema_view(
    get=extend_schema(
        tags=["Driver – Bank Details"],
        summary="Get bank details",
        description="Retrieve the driver's saved bank account details. Returns 404 if not set yet.",
        responses={
            200: BankDetailsSerializer,
            404: OpenApiResponse(description="No bank details on record."),
        },
    ),
    patch=extend_schema(
        tags=["Driver – Bank Details"],
        summary="Create or update bank details",
        description=(
            "Create bank details on first call (returns 201). "
            "Subsequent calls partially update the existing record (returns 200)."
        ),
        request=BankDetailsSerializer,
        responses={
            200: BankDetailsSerializer,
            201: BankDetailsSerializer,
            400: OpenApiResponse(description="Validation error."),
        },
        examples=[
            OpenApiExample(
                "Save bank details",
                value={
                    "account_holder": "Rajan Kumar",
                    "account_number": "1234567890",
                    "ifsc_code": "SBIN0001234",
                    "bank_name": "State Bank of India",
                    "branch_name": "Andheri West",
                    "upi_id": "rajan@upi",
                },
                request_only=True,
            ),
        ],
    ),
)
class BankDetailsView(APIView):
    """
    GET   /drivers/bank-details/ — retrieve bank details (404 if not set)
    PATCH /drivers/bank-details/ — create or update bank details
    """
    permission_classes = [IsDriver]

    def _get_bank_or_none(self, driver):
        try:
            return driver.bank_details
        except BankDetails.DoesNotExist:
            return None

    def get(self, request):
        driver = get_driver(request)
        bank   = self._get_bank_or_none(driver)
        if bank is None:
            return Response({'detail': 'No bank details on record.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(BankDetailsSerializer(bank).data)

    def patch(self, request):
        driver = get_driver(request)
        bank   = self._get_bank_or_none(driver)
        if bank is None:
            # Create on first PATCH
            serializer = BankDetailsSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            bank = serializer.save(driver=driver)
            return Response(BankDetailsSerializer(bank).data, status=status.HTTP_201_CREATED)
        serializer = BankDetailsSerializer(bank, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Earnings
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Driver – Earnings & Stats"],
    summary="Get earnings breakdown",
    description=(
        "Returns credit transaction aggregates for the requested period. "
        "Use `?period=weekly` (default, last 7 days) or `?period=monthly` (last 30 days)."
    ),
    parameters=[
        OpenApiParameter(
            name="period",
            location=OpenApiParameter.QUERY,
            description="Reporting period: `weekly` (default) or `monthly`.",
            required=False,
            type=OpenApiTypes.STR,
            enum=["weekly", "monthly"],
        ),
    ],
    responses={200: EarningsBreakdownSerializer},
)
class EarningsView(APIView):
    """
    GET /drivers/earnings/?period=weekly|monthly
    Returns credit transaction aggregates for the requested period.
    """
    permission_classes = [IsDriver]

    def get(self, request):
        driver = get_driver(request)
        period = request.query_params.get('period', 'weekly').lower()

        if period == 'monthly':
            days  = 30
            label = 'monthly'
        else:
            days  = 7
            label = 'weekly'

        since = timezone.now() - timedelta(days=days)

        try:
            wallet = driver.wallet
        except Wallet.DoesNotExist:
            wallet = None

        if wallet is None:
            data = {'period': label, 'total_earned': Decimal('0.00'),
                    'total_rides': 0, 'average_per_ride': Decimal('0.00')}
        else:
            qs = wallet.transactions.filter(
                txn_type=TransactionType.CREDIT,
                created_at__gte=since,
            )
            agg         = qs.aggregate(total=Sum('amount'), count=Count('id'))
            total       = agg['total'] or Decimal('0.00')
            total_rides = agg['count'] or 0
            avg         = (total / total_rides) if total_rides else Decimal('0.00')
            data = {
                'period': label,
                'total_earned': total,
                'total_rides': total_rides,
                'average_per_ride': round(avg, 2),
            }

        serializer = EarningsBreakdownSerializer(data)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Driver – Earnings & Stats"],
    summary="Get driver stats",
    description="Returns aggregate statistics: total rides, acceptance rate, rating, and verification status.",
    responses={200: DriverStatsSerializer},
)
class StatsView(APIView):
    """GET /drivers/stats/ — rides count, acceptance rate, rating."""
    permission_classes = [IsDriver]

    def get(self, request):
        driver = get_driver(request)
        data   = {
            'total_rides':     driver.total_rides,
            'acceptance_rate': driver.acceptance_rate,
            'rating':          driver.rating,
            'is_verified':     driver.is_verified,
            'status':          driver.status,
        }
        serializer = DriverStatsSerializer(data)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Trip History
# ---------------------------------------------------------------------------

class TripHistoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema(
    tags=["Driver – Trip History"],
    summary="Get trip history",
    description=(
        "Returns a paginated list of CREDIT transactions as a proxy for trip history. "
        "Will be replaced with ride model queries once the rides app is fully wired up."
    ),
    parameters=[
        OpenApiParameter(
            name="page",
            location=OpenApiParameter.QUERY,
            description="Page number (default: 1).",
            required=False,
            type=OpenApiTypes.INT,
        ),
        OpenApiParameter(
            name="page_size",
            location=OpenApiParameter.QUERY,
            description="Number of results per page (default: 20, max: 100).",
            required=False,
            type=OpenApiTypes.INT,
        ),
    ],
    responses={200: TripHistorySerializer(many=True)},
)
class TripHistoryView(APIView):
    """
    GET /drivers/trip-history/?page=1&page_size=20
    Returns paginated CREDIT transactions as a proxy for trip history.
    Replace with Ride model queries once the rides app is wired up.
    """
    permission_classes = [IsDriver]

    def get(self, request):
        driver = get_driver(request)

        try:
            wallet = driver.wallet
            qs = wallet.transactions.filter(txn_type=TransactionType.CREDIT)
        except Wallet.DoesNotExist:
            qs = Transaction.objects.none()

        paginator = TripHistoryPagination()
        page      = paginator.paginate_queryset(qs, request)

        trips = [
            {
                'id':          t.id,
                'date':        t.created_at,
                'amount':      t.amount,
                'description': t.description,
                'reference':   t.reference,
            }
            for t in (page or [])
        ]
        serializer = TripHistorySerializer(trips, many=True)
        return paginator.get_paginated_response(serializer.data)


# ---------------------------------------------------------------------------
# Incentives
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Driver – Incentives"],
    summary="Get active incentives",
    description=(
        "Returns all currently active incentives with the driver's individual progress toward each one. "
        "An incentive is active when today's date falls within its start_date and end_date range."
    ),
    responses={200: DriverIncentiveProgressSerializer(many=True)},
)
class IncentivesView(APIView):
    """
    GET /drivers/incentives/
    Returns active incentives with driver's progress toward each.
    """
    permission_classes = [IsDriver]

    def get(self, request):
        driver = get_driver(request)
        today  = timezone.now().date()

        active_incentives = Incentive.objects.filter(
            is_active=True,
            start_date__lte=today,
            end_date__gte=today,
        )

        results = []
        for incentive in active_incentives:
            progress, _ = DriverIncentiveProgress.objects.get_or_create(
                driver=driver,
                incentive=incentive,
            )
            results.append(progress)

        serializer = DriverIncentiveProgressSerializer(results, many=True)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Driver – Location"],
    summary="Update driver location",
    description=(
        "Submit the driver's current GPS coordinates. "
        "Creates a new location record on first call (201) and updates it on subsequent calls (200)."
    ),
    request=DriverLocationSerializer,
    responses={
        200: DriverLocationSerializer,
        201: DriverLocationSerializer,
        400: OpenApiResponse(description="Validation error."),
    },
    examples=[
        OpenApiExample(
            "Update location",
            value={
                "latitude": "19.076090",
                "longitude": "72.877426",
                "heading": 45.0,
                "speed": 30.5,
            },
            request_only=True,
        ),
    ],
)
class LocationView(APIView):
    """POST /drivers/location/ — update driver GPS coordinates."""
    permission_classes = [IsDriver]

    def post(self, request):
        driver = get_driver(request)
        serializer = DriverLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        location, created = DriverLocation.objects.update_or_create(
            driver=driver,
            defaults={
                'latitude':   data['latitude'],
                'longitude':  data['longitude'],
                'heading':    data.get('heading'),
                'speed':      data.get('speed'),
                'updated_at': timezone.now(),
            },
        )

        return Response(
            DriverLocationSerializer(location).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
