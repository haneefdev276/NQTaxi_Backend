from django.urls import path

from .views import (
    CreateSOSView,
    ListSOSView,
    ResolveSOSView,
)

urlpatterns = [
    path('sos/', CreateSOSView.as_view(), name='create-sos'),
    path('sos/list/', ListSOSView.as_view(), name='list-sos'),
    path('sos/<int:pk>/resolve/', ResolveSOSView.as_view(), name='resolve-sos'),
]