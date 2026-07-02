import hashlib
import hmac

from django.conf import settings
from django.db import transaction

from apps.customers.models import RiderProfile, WalletTransaction


def dev_razorpay_payment_id(order_id):
    return f'dev_{order_id}'


def dev_razorpay_signature(order_id, payment_id):
    message = f'{order_id}|{payment_id}'
    return hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def is_dev_payment(payment_id):
    return str(payment_id).startswith('dev_')


def verify_dev_payment_signature(order_id, payment_id, signature):
    expected = dev_razorpay_signature(order_id, payment_id)
    return hmac.compare_digest(expected, signature)


def credit_wallet_topup(wallet_txn, payment_id):
    with transaction.atomic():
        wallet_txn = WalletTransaction.objects.select_for_update().get(pk=wallet_txn.pk)
        if wallet_txn.status == WalletTransaction.Status.COMPLETED:
            rider_profile = RiderProfile.objects.get(pk=wallet_txn.rider_id)
            return rider_profile, wallet_txn

        rider_profile = RiderProfile.objects.select_for_update().get(pk=wallet_txn.rider_id)
        rider_profile.wallet_balance += wallet_txn.amount
        rider_profile.save(update_fields=['wallet_balance', 'updated_at'])
        wallet_txn.razorpay_payment_id = payment_id
        wallet_txn.status = WalletTransaction.Status.COMPLETED
        wallet_txn.save(update_fields=['razorpay_payment_id', 'status', 'updated_at'])

        from apps.core.utils import paise_to_rupees
        from apps.notifications.utils import create_notification

        create_notification(
            user=rider_profile.user,
            title='Wallet topped up',
            body=f'₹{paise_to_rupees(wallet_txn.amount):.2f} added to your wallet.',
            notification_type='wallet_topup',
            data={
                'transaction_id': str(wallet_txn.id),
                'amount_paise': wallet_txn.amount,
            },
        )
        return rider_profile, wallet_txn
