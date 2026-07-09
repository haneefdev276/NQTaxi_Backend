"""
Custom DRF permissions for the trips app.
"""

from rest_framework.permissions import BasePermission


class IsRider(BasePermission):
    """
    Grants access only to authenticated users who have a RiderProfile.
    """
    message = 'A rider profile is required to access this resource.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'rider_profile')
        )


class IsDriverUser(BasePermission):
    """
    Grants access only to authenticated users who have a DriverProfile.
    Mirrors apps.drivers.permissions.IsDriver but lives here to avoid circular imports.
    """
    message = 'A driver profile is required to access this resource.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'driver_profile')
        )


class IsRiderOrDriver(BasePermission):
    """
    Grants access to either a rider or a driver.
    """
    message = 'Authentication with a rider or driver profile is required.'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return (
            hasattr(request.user, 'rider_profile')
            or hasattr(request.user, 'driver_profile')
        )
