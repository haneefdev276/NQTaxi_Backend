"""
URL configuration for the users app.
"""
from django.urls import path
from .views import CustomerRegistrationView, DriverRegistrationView

app_name = 'users'

urlpatterns = [
    path('register/customer/', CustomerRegistrationView.as_view(), name='register_customer'),
    path('register/driver/', DriverRegistrationView.as_view(), name='register_driver'),
]
