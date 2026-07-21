"""
Custom DRF exception handler.

Wraps all DRF error responses in the standard NQTaxi envelope:
    {
        "success": false,
        "message": "Human-readable error description",
        "data": null,
        "timestamp": "2026-07-09T16:30:00Z"
    }

Register in settings.py:
    REST_FRAMEWORK = {
        ...
        'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
    }
"""

from django.utils import timezone
from rest_framework.views import exception_handler


def _timestamp() -> str:
    return timezone.now().strftime('%Y-%m-%dT%H:%M:%SZ')


def _flatten_errors(data) -> str:
    """
    Convert DRF's nested error structures into a single human-readable string.

    Examples:
        {"detail": "Not found."} → "Not found."
        {"email": ["Enter a valid email."]} → "email: Enter a valid email."
        {"non_field_errors": ["Already exists."]} → "Already exists."
    """
    if isinstance(data, str):
        return data

    if isinstance(data, list):
        return ' '.join(str(e) for e in data)

    if isinstance(data, dict):
        # DRF detail key (authentication / permission errors)
        if 'detail' in data:
            return str(data['detail'])

        parts = []
        for field, errors in data.items():
            if field == 'non_field_errors':
                # Don't prefix with field name for top-level validation errors
                if isinstance(errors, list):
                    parts.extend(str(e) for e in errors)
                else:
                    parts.append(str(errors))
            else:
                if isinstance(errors, list):
                    parts.append(f"{field}: {', '.join(str(e) for e in errors)}")
                else:
                    parts.append(f"{field}: {errors}")
        return ' | '.join(parts) if parts else 'An error occurred.'

    return str(data)


def custom_exception_handler(exc, context):
    """DRF exception handler that wraps responses in the NQTaxi envelope."""
    response = exception_handler(exc, context)

    if response is not None:
        message = _flatten_errors(response.data)
        response.data = {
            "success": False,
            "message": message,
            "data": None,
            "timestamp": _timestamp(),
        }

    return response
