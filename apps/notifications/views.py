from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.serializers import (
    EmptyBodySerializer,
    FCMDeviceTokenSerializer,
    FCMTokenRegisterResponseSerializer,
    FCMTokenRegisterSerializer,
    NotificationErrorResponseSerializer,
    NotificationListResponseSerializer,
    NotificationMarkReadResponseSerializer,
    NotificationReadAllRequestSerializer,
    NotificationReadAllResponseSerializer,
    NotificationSerializer,
)


@extend_schema(
    tags=['Notifications'],
    summary='List notifications (unread first)',
    responses={200: NotificationListResponseSerializer},
)
class NotificationListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('is_read', '-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        unread_count = queryset.filter(is_read=False).count()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        notifications = serializer.data
        total_count = queryset.count()

        response_data = {
            'success': True,
            'message': 'No notifications found' if total_count == 0 else 'Notifications retrieved successfully',
            'notifications': notifications,
            'unread_count': unread_count,
        }

        if page is not None:
            paginated = self.get_paginated_response(serializer.data)
            response_data.update({
                'count': paginated.data.get('count'),
                'next': paginated.data.get('next'),
                'previous': paginated.data.get('previous'),
                'notifications': paginated.data.get('results', []),
            })

        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notifications'],
    summary='Mark a notification as read',
    request=EmptyBodySerializer,
    responses={
        200: NotificationMarkReadResponseSerializer,
        404: NotificationErrorResponseSerializer,
    },
)
class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(user=request.user, pk=pk)
        except Notification.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': 'Notification not found.',
                    'code': 'NOTIFICATION_NOT_FOUND',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at', 'updated_at'])

        return Response(
            {
                'success': True,
                'message': 'Notification marked as read',
                'notification': NotificationSerializer(notification).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=['Notifications'],
    summary='Mark all notifications as read',
    request=NotificationReadAllRequestSerializer,
    responses={201: NotificationReadAllResponseSerializer},
)
class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_notifications = Notification.objects.filter(user=request.user)
        total_count = user_notifications.count()
        updated = user_notifications.filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now(),
        )

        if updated > 0:
            message = 'All notifications marked as read'
        elif total_count == 0:
            message = 'No notifications found'
        else:
            message = 'All notifications already marked as read'

        return Response(
            {
                'success': True,
                'message': message,
                'updated_count': updated,
                'unread_count': 0,
                'total_count': total_count,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=['Notifications'],
    summary='Register device FCM token',
    request=FCMTokenRegisterSerializer,
    responses={201: FCMTokenRegisterResponseSerializer},
)
class FCMTokenRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FCMTokenRegisterSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        device_token = serializer.save()
        return Response(
            {
                'success': True,
                'message': 'FCM token registered successfully',
                'fcm_token': FCMDeviceTokenSerializer(device_token).data,
            },
            status=status.HTTP_201_CREATED,
        )
