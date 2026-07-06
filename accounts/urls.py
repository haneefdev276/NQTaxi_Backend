from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    LoginView,
    MeView,
    SendOTPView,
    VerifyOTPView,
    LogoutView,
    ForgotPasswordView,
    ResetPasswordView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('login/', LoginView.as_view(), name='login'),

    # Refresh Token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Logout
    path('logout/', LogoutView.as_view(), name='logout'),

    # Forgot Password
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),

    # Reset Password
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),

    # Current User
    path('me/', MeView.as_view(), name='me'),
]