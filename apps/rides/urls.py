"""
URL configuration for the rides app.

All views live in apps.trips.views but are exposed under /api/v1/rides/
to keep the public API consistent with the frontend contract.
"""

from django.urls import path

from apps.trips.views import (
    TripRequestView,
    TripListView,
    TripDetailView,
    TripAcceptView,
    TripRejectView,
    TripStartView,
    TripCompleteView,
    TripCancelView,
    ActiveTripView,
    NearbyDriversView,
)

app_name = 'rides'

urlpatterns = [
    # -----------------------------------------------------------------------
    # Rider-initiated
    # -----------------------------------------------------------------------
    path('request/',         TripRequestView.as_view(),   name='trip-request'),
    path('active/',          ActiveTripView.as_view(),    name='trip-active'),
    path('nearby-drivers/',  NearbyDriversView.as_view(), name='nearby-drivers'),

    # -----------------------------------------------------------------------
    # List & detail
    # -----------------------------------------------------------------------
    path('',                 TripListView.as_view(),      name='trip-list'),
    path('<uuid:pk>/',       TripDetailView.as_view(),    name='trip-detail'),

    # -----------------------------------------------------------------------
    # State-machine transitions
    # -----------------------------------------------------------------------
    path('<uuid:pk>/accept/',   TripAcceptView.as_view(),   name='trip-accept'),
    path('<uuid:pk>/reject/',   TripRejectView.as_view(),   name='trip-reject'),
    path('<uuid:pk>/start/',    TripStartView.as_view(),    name='trip-start'),
    path('<uuid:pk>/complete/', TripCompleteView.as_view(), name='trip-complete'),
    path('<uuid:pk>/cancel/',   TripCancelView.as_view(),   name='trip-cancel'),
]
