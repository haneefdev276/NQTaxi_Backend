from django.urls import path

from apps.users.views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    RegisterView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
]
