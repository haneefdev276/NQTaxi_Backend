from django.urls import path,include
from . import views

urlpatterns = [
    path('create-order/',views.create_order, name='create-order'),
    path('verify-payment/',views.verify_payment, name='verify-payment'),
    path('webhook/',views.payment_webhook, name='payment-webhook'),
    path('refund/',views.refund_payment, name='refund-payment'),
    path('transaction-history/',views.transaction_history, name='transaction-history'),
]
