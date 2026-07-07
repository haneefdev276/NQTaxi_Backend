from django.urls import path

from apps.notifications.views import (
    FCMTokenRegisterView,
    NotificationListView,
    NotificationMarkReadView,
    NotificationReadAllView,
)

urlpatterns = [
    path('', NotificationListView.as_view()),
    path('read-all/', NotificationReadAllView.as_view()),
    path('fcm-token/', FCMTokenRegisterView.as_view()),
    path('<uuid:pk>/read/', NotificationMarkReadView.as_view()),
]
