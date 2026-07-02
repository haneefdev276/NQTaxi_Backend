from rest_framework.permissions import BasePermission


class IsRiderOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return getattr(request.user, 'rider_profile', None) == getattr(obj, 'rider', None)
