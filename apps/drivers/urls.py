"""
URL configuration for the drivers app.
All paths are prefixed with /api/v1/drivers/ from the root urls.py.
"""

from django.urls import path
from .views import (
    DriverProfileView,
    VehicleView,
    DocumentListView,
    DocumentUploadView,
    DocumentDeleteView,
    DriverStatusView,
    WalletView,
    WithdrawView,
    BankDetailsView,
    EarningsView,
    StatsView,
    TripHistoryView,
    IncentivesView,
    LocationView,
)

app_name = 'drivers'

urlpatterns = [
    # Profile
    path('profile/',              DriverProfileView.as_view(),   name='profile'),

    # Vehicle
    path('vehicle/',              VehicleView.as_view(),          name='vehicle'),

    # Documents
    path('documents/',            DocumentListView.as_view(),     name='document-list'),
    path('documents/upload/',     DocumentUploadView.as_view(),   name='document-upload'),
    path('documents/<int:pk>/',   DocumentDeleteView.as_view(),   name='document-delete'),

    # Status
    path('status/',               DriverStatusView.as_view(),     name='status'),

    # Wallet & earnings
    path('wallet/',               WalletView.as_view(),           name='wallet'),
    path('wallet/withdraw/',      WithdrawView.as_view(),         name='wallet-withdraw'),

    # Bank details
    path('bank-details/',         BankDetailsView.as_view(),      name='bank-details'),

    # Reporting
    path('earnings/',             EarningsView.as_view(),         name='earnings'),
    path('stats/',                StatsView.as_view(),            name='stats'),
    path('trip-history/',         TripHistoryView.as_view(),      name='trip-history'),

    # Incentives
    path('incentives/',           IncentivesView.as_view(),       name='incentives'),

    # Location
    path('location/',             LocationView.as_view(),         name='location'),
]
