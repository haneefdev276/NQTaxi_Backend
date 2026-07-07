from rest_framework import serializers

class CreateOrderSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class VerifyPaymentSerializer(serializers.Serializer):#created a new serializer for verifying the payment
    razorpay_order_id = serializers.CharField(max_length=255)
    razorpay_payment_id = serializers.CharField(max_length=255)
    razorpay_signature = serializers.CharField(max_length=255)