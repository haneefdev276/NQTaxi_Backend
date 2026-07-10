from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('apps.users.urls')),
    path('api/v1/auth/', include('apps.users.urls')),
    path('customers/', include('apps.customers.urls')),
    path('api/v1/customers/', include('apps.customers.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path("api/v1/support/",include("supportapps.urls")),
]
