import logging

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class CustomersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.customers'

    def ready(self):
        logger = logging.getLogger(__name__)
        key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
        key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')

        if settings.DEBUG:
            logger.debug('RAZORPAY_KEY_ID=%r', key_id)

        missing = (
            not key_id
            or not key_secret
            or key_id.startswith('your_')
            or key_secret.startswith('your_')
            or key_id.endswith('_here')
        )
        if missing:
            message = (
                'RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set in .env for wallet APIs. '
                'Copy .env.example to .env and add Razorpay test credentials.'
            )
            if settings.DEBUG:
                logger.warning(message)
                return
            raise ImproperlyConfigured(message)

        if key_id == key_secret or (len(key_secret) > 8 and key_secret in key_id):
            raise ImproperlyConfigured(
                'RAZORPAY_KEY_ID appears to include the key secret. Set key ID and secret as separate values in .env.'
            )

        if len(key_id) < 20:
            logger.warning(
                'RAZORPAY_KEY_ID looks short (%d chars). If wallet top-up fails, copy the full Key ID '
                'from Razorpay dashboard (format: rzp_test_XXXXXXXXXXXXXX).',
                len(key_id),
            )
