from decimal import Decimal
import logging

import razorpay
from django.conf import settings
from django.http import Http404
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Avg
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import DestroyAPIView, ListAPIView, ListCreateAPIView, RetrieveUpdateAPIView, UpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.customers.models import EmergencyContact, PaymentMethod, RiderProfile, SavedPlace, WalletTransaction
from apps.customers.serializers import (
    EmergencyContactSerializer,
    PaymentMethodSerializer,
    RiderProfileSerializer,
    RiderProfileUpdateSerializer,
    SavedPlaceSerializer,
    TripHistorySerializer,
    WalletSerializer,
    WalletTopupSerializer,
    WalletTopupDevConfirmSerializer,
    WalletTopupVerifySerializer,
    WalletTransactionSerializer,
    RatingSerializer,
)
from apps.customers.utils import get_rider_profile
from apps.customers.wallet import (
    credit_wallet_topup,
    dev_razorpay_payment_id,
    dev_razorpay_signature,
    is_dev_payment,
    verify_dev_payment_signature,
)
from apps.core.utils import rupees_to_paise, paise_to_rupees


@extend_schema_view(
    get=extend_schema(
        tags=['Profile'],
        summary='Get rider profile',
        responses={200: OpenApiResponse(response=dict, description='Profile wrapped in success payload')},
    ),
    put=extend_schema(
        tags=['Profile'],
        summary='Update rider profile',
        request=RiderProfileUpdateSerializer,
        responses={200: OpenApiResponse(response=dict, description='Updated profile wrapped in success payload')},
    ),
    patch=extend_schema(
        tags=['Profile'],
        summary='Partially update rider profile',
        request=RiderProfileUpdateSerializer,
        responses={200: OpenApiResponse(response=dict, description='Updated profile wrapped in success payload')},
    ),
)
class ProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RiderProfileSerializer

    def get_object(self):
        return get_rider_profile(self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                'success': True,
                'message': 'Profile retrieved successfully',
                'profile': serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = RiderProfileUpdateSerializer(
            instance,
            data=request.data,
            partial=partial,
            context=self.get_serializer_context(),
        )
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(
            {
                'success': True,
                'message': 'Profile updated successfully',
                'profile': RiderProfileSerializer(instance, context=self.get_serializer_context()).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(tags=['Saved Places'], summary='List saved places'),
    post=extend_schema(tags=['Saved Places'], summary='Create a saved place'),
)
class SavedPlaceListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SavedPlaceSerializer

    def get_queryset(self):
        return SavedPlace.objects.filter(rider=get_rider_profile(self.request.user)).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(rider=get_rider_profile(self.request.user))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_create(serializer)
        return Response(
            {
                'success': True,
                'message': 'Saved place added successfully',
                'saved_place': serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)

        response_data = {
            'success': True,
            'message': 'Saved places retrieved successfully',
            'saved_places': serializer.data,
        }

        if page is not None:
            paginated = self.get_paginated_response(serializer.data)
            response_data.update({
                'count': paginated.data.get('count'),
                'next': paginated.data.get('next'),
                'previous': paginated.data.get('previous'),
                'saved_places': paginated.data.get('results', []),
            })

        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema_view(
    put=extend_schema(tags=['Saved Places'], summary='Update a saved place'),
    delete=extend_schema(tags=['Saved Places'], summary='Delete a saved place'),
)
class SavedPlaceDetailView(UpdateAPIView, DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SavedPlaceSerializer

    def get_queryset(self):
        return SavedPlace.objects.filter(rider=get_rider_profile(self.request.user))

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_update(serializer)
        return Response(
            {
                'success': True,
                'message': 'Saved place updated successfully',
                'saved_place': serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        deleted_id = str(instance.pk)
        self.perform_destroy(instance)
        return Response(
            {
                'success': True,
                'message': 'Saved place deleted successfully',
                'deleted_id': deleted_id,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(tags=['Payment Methods'], summary='List saved payment methods'),
    post=extend_schema(tags=['Payment Methods'], summary='Add a payment method'),
)
class PaymentMethodListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        return PaymentMethod.objects.filter(rider=get_rider_profile(self.request.user)).order_by('-created_at')

    def perform_create(self, serializer):
        rider = get_rider_profile(self.request.user)
        with transaction.atomic():
            if serializer.validated_data.get('is_default'):
                PaymentMethod.objects.filter(rider=rider).update(is_default=False)
            serializer.save(rider=rider)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_create(serializer)
        return Response(
            {
                'success': True,
                'message': 'Payment method added successfully',
                'payment_method': serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)

        response_data = {
            'success': True,
            'message': 'Payment methods retrieved successfully',
            'payment_methods': serializer.data,
        }

        if page is not None:
            paginated = self.get_paginated_response(serializer.data)
            response_data.update({
                'count': paginated.data.get('count'),
                'next': paginated.data.get('next'),
                'previous': paginated.data.get('previous'),
                'payment_methods': paginated.data.get('results', []),
            })

        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(tags=['Payment Methods'], summary='Delete a payment method')
class PaymentMethodDeleteView(DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        return PaymentMethod.objects.filter(rider=get_rider_profile(self.request.user))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        deleted_id = str(instance.pk)
        self.perform_destroy(instance)
        return Response(
            {
                'success': True,
                'message': 'Payment method deleted successfully',
                'deleted_id': deleted_id,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=['Payment Methods'], summary='Set a payment method as default', request=None, responses=OpenApiResponse(response=PaymentMethodSerializer))
class SetDefaultPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        rider = get_rider_profile(request.user)
        payment_method = get_object_or_404(PaymentMethod.objects.filter(rider=rider), pk=pk)
        with transaction.atomic():
            PaymentMethod.objects.select_for_update().filter(rider=rider).exclude(pk=payment_method.pk).update(is_default=False)
            payment_method.is_default = True
            payment_method.save(update_fields=['is_default'])
        return Response(
            {
                'success': True,
                'message': 'Payment method set as default',
                'payment_method': PaymentMethodSerializer(payment_method).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(tags=['Emergency Contacts'], summary='List emergency contacts'),
    post=extend_schema(tags=['Emergency Contacts'], summary='Add an emergency contact'),
)
class EmergencyContactListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmergencyContactSerializer

    def get_queryset(self):
        return EmergencyContact.objects.filter(rider=get_rider_profile(self.request.user)).order_by('-created_at')

    def perform_create(self, serializer):
        rider = get_rider_profile(self.request.user)
        with transaction.atomic():
            if serializer.validated_data.get('is_primary'):
                EmergencyContact.objects.filter(rider=rider).update(is_primary=False)
            serializer.save(rider=rider)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_create(serializer)
        return Response(
            {
                'success': True,
                'message': 'Emergency contact added successfully',
                'contact': serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)

        response_data = {
            'success': True,
            'message': 'Emergency contacts retrieved successfully',
            'contacts': serializer.data,
        }

        if page is not None:
            paginated = self.get_paginated_response(serializer.data)
            response_data.update({
                'count': paginated.data.get('count'),
                'next': paginated.data.get('next'),
                'previous': paginated.data.get('previous'),
                'contacts': paginated.data.get('results', []),
            })

        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(tags=['Emergency Contacts'], summary='Delete an emergency contact')
class EmergencyContactDeleteView(DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmergencyContactSerializer

    def get_queryset(self):
        return EmergencyContact.objects.filter(rider=get_rider_profile(self.request.user))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        deleted_id = str(instance.pk)
        self.perform_destroy(instance)
        return Response(
            {
                'success': True,
                'message': 'Emergency contact deleted successfully',
                'deleted_id': deleted_id,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=['Wallet'], summary='Get wallet balance and transactions', responses=OpenApiResponse(response=WalletSerializer))
class WalletView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rider = get_rider_profile(request.user)
        rider.refresh_from_db(fields=['wallet_balance'])
        transactions = WalletTransaction.objects.filter(rider=rider).order_by('-created_at')

        paginator = PageNumberPagination()
        paginator.page_size = 10
        page = paginator.paginate_queryset(transactions, request)
        serialized = WalletTransactionSerializer(page if page is not None else transactions, many=True).data

        response_data = {
            'success': True,
            'message': 'Wallet retrieved successfully',
            'balance_rupees': paise_to_rupees(rider.wallet_balance),
            'transactions': serialized,
        }

        if page is not None:
            paginated = paginator.get_paginated_response(serialized)
            response_data.update({
                'count': paginated.data.get('count'),
                'next': paginated.data.get('next'),
                'previous': paginated.data.get('previous'),
                'transactions': paginated.data.get('results', []),
            })

        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(tags=['Wallet'], summary='Initiate a wallet top-up', request=WalletTopupSerializer, responses=OpenApiResponse(response=dict))
class WalletTopupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WalletTopupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        amount_rupees = serializer.validated_data['amount_rupees']
        amount_paise = int(Decimal(str(amount_rupees)) * 100)

        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order = client.order.create({
                'amount': amount_paise,
                'currency': 'INR',
                'payment_capture': 1,
            })
        except razorpay.errors.BadRequestError as exc:
            logger = logging.getLogger(__name__)
            if settings.DEBUG:
                logger.error('Razorpay order.create failed: %s', exc)
            return Response(
                {
                    'success': False,
                    'error': 'Payment gateway authentication failed. Please contact support.',
                    'code': 'GATEWAY_AUTH_ERROR',
                    **({'detail': str(exc)} if settings.DEBUG else {}),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception:
            return Response(
                {
                    'success': False,
                    'error': 'Unable to process the payment gateway request. Please try again later.',
                    'code': 'GATEWAY_ERROR',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        rider = get_rider_profile(request.user)
        wallet_txn = WalletTransaction.objects.create(
            rider=rider,
            type=WalletTransaction.TransactionType.CREDIT,
            amount=amount_paise,
            description='Wallet top-up',
            razorpay_order_id=order['id'],
            status=WalletTransaction.Status.PENDING,
        )

        dev_payment_id = dev_razorpay_payment_id(order['id'])
        dev_signature = dev_razorpay_signature(order['id'], dev_payment_id)

        auto_completed = False
        if settings.DEBUG and settings.RAZORPAY_AUTO_COMPLETE_TOPUP:
            rider, wallet_txn = credit_wallet_topup(wallet_txn, dev_payment_id)
            auto_completed = True

        response_data = {
            'success': True,
            'transaction_id': str(wallet_txn.id),
            'razorpay_order_id': order['id'],
            'amount_paise': amount_paise,
            'amount_rupees': paise_to_rupees(amount_paise),
            'currency': 'INR',
            'key': settings.RAZORPAY_KEY_ID,
            'auto_completed': auto_completed,
        }
        if settings.DEBUG:
            response_data['razorpay_payment_id'] = dev_payment_id
            response_data['razorpay_signature'] = dev_signature
        if auto_completed:
            response_data['balance_rupees'] = paise_to_rupees(rider.wallet_balance)
            response_data['message'] = 'Wallet topped up successfully (dev auto-complete).'

        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Wallet'],
    summary='Verify a wallet top-up payment',
    request=WalletTopupVerifySerializer,
    responses=OpenApiResponse(response=dict),
)
class WalletTopupVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WalletTopupVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        order_id = serializer.validated_data['razorpay_order_id']
        payment_id = serializer.validated_data['razorpay_payment_id']
        signature = serializer.validated_data['razorpay_signature']
        rider = get_rider_profile(request.user)

        try:
            wallet_txn = WalletTransaction.objects.get(
                rider=rider,
                razorpay_order_id=order_id,
            )
        except WalletTransaction.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': 'Top-up order not found.',
                    'code': 'ORDER_NOT_FOUND',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if wallet_txn.status == WalletTransaction.Status.COMPLETED:
            rider.refresh_from_db(fields=['wallet_balance'])
            return Response(
                {
                    'success': True,
                    'message': 'Payment already verified.',
                    'balance_rupees': paise_to_rupees(rider.wallet_balance),
                    'transaction': WalletTransactionSerializer(wallet_txn).data,
                },
                status=status.HTTP_200_OK,
            )

        try:
            if settings.DEBUG and is_dev_payment(payment_id):
                if not verify_dev_payment_signature(order_id, payment_id, signature):
                    raise razorpay.errors.SignatureVerificationError('Invalid dev payment signature')
            else:
                client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                client.utility.verify_payment_signature({
                    'razorpay_order_id': order_id,
                    'razorpay_payment_id': payment_id,
                    'razorpay_signature': signature,
                })
        except razorpay.errors.SignatureVerificationError:
            wallet_txn.status = WalletTransaction.Status.FAILED
            wallet_txn.save(update_fields=['status', 'updated_at'])
            return Response(
                {
                    'success': False,
                    'error': 'Payment verification failed.',
                    'code': 'PAYMENT_VERIFICATION_FAILED',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            rider_profile, wallet_txn = credit_wallet_topup(wallet_txn, payment_id)

        return Response(
            {
                'success': True,
                'message': 'Wallet topped up successfully.',
                'balance_rupees': paise_to_rupees(rider_profile.wallet_balance),
                'transaction': WalletTransactionSerializer(wallet_txn).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=['Wallet'],
    summary='Dev-only: confirm a pending wallet top-up without Razorpay checkout',
    request=WalletTopupDevConfirmSerializer,
    responses=OpenApiResponse(response=dict),
)
class WalletTopupDevConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.DEBUG:
            raise Http404()

        serializer = WalletTopupDevConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        order_id = serializer.validated_data['razorpay_order_id']
        rider = get_rider_profile(request.user)

        try:
            wallet_txn = WalletTransaction.objects.get(
                rider=rider,
                razorpay_order_id=order_id,
            )
        except WalletTransaction.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': 'Top-up order not found.',
                    'code': 'ORDER_NOT_FOUND',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        rider_profile, wallet_txn = credit_wallet_topup(wallet_txn, f'dev_{order_id}')
        return Response(
            {
                'success': True,
                'message': 'Wallet topped up successfully (dev confirm).',
                'balance_rupees': paise_to_rupees(rider_profile.wallet_balance),
                'transaction': WalletTransactionSerializer(wallet_txn).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=['Debug'], summary='Debug Razorpay key loading')
class RazorpayDebugView(APIView):
    def get(self, request):
        if not settings.DEBUG:
            raise Http404()

        key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
        secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
        key_id_set = bool(key_id)
        secret_set = bool(secret)
        mode = None
        if key_id.startswith('rzp_test_'):
            mode = 'test'
        elif key_id.startswith('rzp_live_'):
            mode = 'live'

        return Response({
            'razorpay_key_id_set': key_id_set,
            'razorpay_key_id_prefix': key_id[:8] if key_id_set else None,
            'razorpay_key_secret_set': secret_set,
            'razorpay_mode': mode,
        }, status=status.HTTP_200_OK)


@extend_schema(tags=['Trip History'], summary='Get paginated trip history', responses=TripHistorySerializer(many=True))
class TripHistoryView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TripHistorySerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        from apps.trips.models import Trip

        return Trip.objects.filter(rider=self.request.user).select_related('driver').order_by('-requested_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)

        response_data = {
            'success': True,
            'message': 'Trip history retrieved successfully',
            'trips': serializer.data,
        }

        if page is not None:
            paginated = self.get_paginated_response(serializer.data)
            response_data.update({
                'count': paginated.data.get('count'),
                'next': paginated.data.get('next'),
                'previous': paginated.data.get('previous'),
                'trips': paginated.data.get('results', []),
            })

        return Response(response_data, status=status.HTTP_200_OK)


class GivenRatingsPagination(PageNumberPagination):
    page_query_param = 'given_page'
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ReceivedRatingsPagination(PageNumberPagination):
    page_query_param = 'received_page'
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema(tags=['Ratings'], summary='Get ratings given and received', request=None, responses=OpenApiResponse(response=dict))
class RatingsView(APIView):
    permission_classes = [IsAuthenticated]

    def _paginated_ratings_payload(self, paginator, page, queryset, serializer_class):
        if page is not None:
            paginated = paginator.get_paginated_response(serializer_class(page, many=True).data)
            return {
                'count': paginated.data.get('count'),
                'next': paginated.data.get('next'),
                'previous': paginated.data.get('previous'),
                'ratings': paginated.data.get('results', []),
            }

        serialized = serializer_class(queryset, many=True).data
        return {
            'count': len(serialized),
            'next': None,
            'previous': None,
            'ratings': serialized,
        }

    def get(self, request):
        rider = request.user
        from apps.ratings.models import Rating  # type: ignore

        given_ratings = Rating.objects.filter(given_by_rider=rider).select_related('trip', 'given_by_rider').order_by('-created_at')
        received_ratings = (
            Rating.objects.filter(trip__rider=rider)
            .exclude(given_by_rider=rider)
            .select_related('trip', 'given_by_rider')
            .order_by('-created_at')
        )

        given_paginator = GivenRatingsPagination()
        received_paginator = ReceivedRatingsPagination()

        given_page = given_paginator.paginate_queryset(given_ratings, request, view=self)
        received_page = received_paginator.paginate_queryset(received_ratings, request, view=self)

        return Response(
            {
                'success': True,
                'message': 'Ratings retrieved successfully',
                'summary': {
                    'average_rating_given': round(float(given_ratings.aggregate(Avg('score'))['score__avg'] or 0.0), 1),
                    'average_rating_received': round(float(received_ratings.aggregate(Avg('score'))['score__avg'] or 0.0), 1),
                    'total_given': given_ratings.count(),
                    'total_received': received_ratings.count(),
                },
                'given': self._paginated_ratings_payload(given_paginator, given_page, given_ratings, RatingSerializer),
                'received': self._paginated_ratings_payload(received_paginator, received_page, received_ratings, RatingSerializer),
            },
            status=status.HTTP_200_OK,
        )
