"""
Custom DRF permissions for the drivers app.
"""

from rest_framework.permissions import BasePermission


class IsDriver(BasePermission):
    """
    Grants access only to authenticated users who have a DriverProfile.
    """
    message = 'A verified driver profile is required to access this resource.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'driver_profile')
        )
