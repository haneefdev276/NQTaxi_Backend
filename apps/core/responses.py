"""
Standard API response helpers for NQTaxi.

Usage:
    from apps.core.responses import api_response, error_response, paginated_api_response

    # Success
    return api_response(data=serializer.data, message="Profile updated successfully")

    # Created
    return api_response(data=serializer.data, message="Document uploaded", http_status=201)

    # Error
    return error_response("Insufficient balance.", http_status=400)

    # No content (e.g. DELETE)
    return api_response(data=None, message="Document deleted", http_status=204)

    # Paginated (pass the paginator + page data)
    return paginated_api_response(paginator, request, serializer.data, "Trips fetched")
"""

from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status as http_status_codes


def _timestamp() -> str:
    """Return the current UTC time in ISO-8601 format."""
    return timezone.now().strftime('%Y-%m-%dT%H:%M:%SZ')


def api_response(
    data=None,
    message: str = "Request completed successfully",
    http_status: int = http_status_codes.HTTP_200_OK,
    success: bool = True,
) -> Response:
    """
    Wraps any payload into the standard NQTaxi response envelope.

    Shape:
    {
        "success": true,
        "message": "...",
        "data": { ... } | [ ... ] | null,
        "timestamp": "2026-07-09T16:30:00Z"
    }
    """
    return Response(
        {
            "success": success,
            "message": message,
            "data": data,
            "timestamp": _timestamp(),
        },
        status=http_status,
    )


def error_response(
    message: str = "An error occurred.",
    http_status: int = http_status_codes.HTTP_400_BAD_REQUEST,
    data=None,
) -> Response:
    """Convenience wrapper for error responses."""
    return api_response(data=data, message=message, http_status=http_status, success=False)


def paginated_api_response(paginator, request, queryset, serializer_class, message: str = "Request completed successfully") -> Response:
    """
    Paginates `queryset`, serializes with `serializer_class`, and wraps in
    the standard envelope. The `data` key will contain:
    {
        "count": 42,
        "next": "http://...",
        "previous": null,
        "results": [...]
    }
    """
    page = paginator.paginate_queryset(queryset, request)
    serializer = serializer_class(page, many=True)
    paginated = paginator.get_paginated_response(serializer.data)
    return Response(
        {
            "success": True,
            "message": message,
            "data": paginated.data,
            "timestamp": _timestamp(),
        }
    )
