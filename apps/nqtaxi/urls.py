"""
URL configuration for nqtaxi project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # JWT Auth
    path('api/v1/auth/token/',         TokenObtainPairView.as_view(),  name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(),     name='token_refresh'),
    path('api/v1/auth/token/verify/',  TokenVerifyView.as_view(),      name='token_verify'),

    # API v1
    path('api/v1/users/',         include('apps.users.urls')),
    path('api/v1/rides/',         include('apps.rides.urls')),
    path('api/v1/drivers/',       include('apps.drivers.urls')),
    path('api/v1/payments/',      include('apps.payments.urls')),
    path('api/v1/customers/',     include('apps.customers.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/fares/',         include('apps.fares.urls')),
    path('api/v1/support/',       include('supportapps.urls')),

    # Swagger Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
