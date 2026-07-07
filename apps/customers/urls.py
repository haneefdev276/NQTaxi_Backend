from django.urls import path

from apps.customers.views import (
    EmergencyContactDeleteView,
    EmergencyContactListCreateView,
    PaymentMethodDeleteView,
    PaymentMethodListCreateView,
    ProfileView,
    RatingsView,
    RazorpayDebugView,
    SavedPlaceDetailView,
    SavedPlaceListCreateView,
    SetDefaultPaymentView,
    TripHistoryView,
    WalletTopupDevConfirmView,
    WalletTopupView,
    WalletTopupVerifyView,
    WalletView,
)

urlpatterns = [
    path('profile/', ProfileView.as_view()),
    path('saved-places/', SavedPlaceListCreateView.as_view()),
    path('saved-places/<uuid:pk>/', SavedPlaceDetailView.as_view()),
    path('payment-methods/', PaymentMethodListCreateView.as_view()),
    path('payment-methods/<uuid:pk>/', PaymentMethodDeleteView.as_view()),
    path('payment-methods/<uuid:pk>/default/', SetDefaultPaymentView.as_view()),
    path('emergency-contacts/', EmergencyContactListCreateView.as_view()),
    path('emergency-contacts/<uuid:pk>/', EmergencyContactDeleteView.as_view()),
    path('wallet/', WalletView.as_view()),
    path('wallet/topup/', WalletTopupView.as_view()),
    path('wallet/topup/verify/', WalletTopupVerifyView.as_view()),
    path('wallet/topup/dev-confirm/', WalletTopupDevConfirmView.as_view()),
    path('debug/razorpay-check/', RazorpayDebugView.as_view()),
    path('trip-history/', TripHistoryView.as_view()),
    path('ratings/', RatingsView.as_view()),
]
