import uuid
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import CreateOrderSerializer, VerifyPaymentSerializer
from .models import Payment
from drf_spectacular.utils import extend_schema


@extend_schema(
    request=CreateOrderSerializer,
    responses={
        201: None},
)
@api_view(['POST'])
def create_order(request):
    print('REQUEST DATA:', request.data)
    serializer = CreateOrderSerializer(data=request.data)
    if serializer.is_valid():
        booking_id = serializer.validated_data['booking_id']    
        amount = serializer.validated_data['amount']
        payment = Payment.objects.create(booking_id=booking_id, amount=amount)
        order_id = f"ORDER_{uuid.uuid4().hex[:12].upper}"

        return Response({"status":"sucess",
                         "message":"Order created successfully",
                         "data":{
                            "order_id":order_id,
                            "payment_id":payment.id,
                            "booking_id": booking_id,
                            "amount": str(amount)
                         }
           }, status=201)
    
    return Response(serializer.errors, status=400)
@extend_schema(
    request=VerifyPaymentSerializer,
    responses={
        200: None},

)
@api_view(['POST'])
def verify_payment(request):
    print('REQUEST DATA:', request.data)
    serializer = VerifyPaymentSerializer(data=request.data)
    if serializer.is_valid():
        razorpay_order_id = serializer.validated_data['razorpay_order_id']
        razorpay_payment_id = serializer.validated_data['razorpay_payment_id']
        razorpay_signature = serializer.validated_data['razorpay_signature']

        payment_id = f"pay_{uuid.uuid4().hex[:12].upper()}"
    return Response({
    "status": "success",
    "message": "Payment verified successfully",
    "data": {
        "payment_id": payment_id,
        "order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "signature": razorpay_signature,
        "verification_status": "verified"
    }
}, status=200)


    return Response(serializer.errors, status=400)
    
@extend_schema(
    request=None,
    responses={200: None},
)
@api_view(['POST'])
def payment_webhook(request): #webhook endpoint to receive payment status updates from Razorpay
    webhook_id = f"WEBHOOK_{uuid.uuid4().hex[:12].upper()}"
    return Response({

    "status": "success",

    "message": "Webhook received successfully",

    "data": {

        "webhook_id": webhook_id

    }

}, status=200)



@extend_schema(
    request=None,
    responses={200: None},
)  

@api_view(['POST']) 
def refund_payment(request): #refund endpoint to process refunds for a payment
   refund_id = f"REFUND_{uuid.uuid4().hex[:12].upper()}"
   return Response({
    "status": "success",
    "message": "Refund processed successfully",
    "data": {
        "refund_id": refund_id,
        "status": "processed"
    }
}, status=200)

@api_view(['GET'])

def transaction_history(request): #endpoint to view transaction history
    payments = Payment.objects.all().values()# fetch all payment records from the database
    transaction_id = f"TRANSACTION_{uuid.uuid4().hex[:12].upper()}"

    return Response({
    "status": "success",
    "message": "Transaction history fetched successfully",
    "data": {
        "transaction_id": transaction_id,
        "transactions": list(payments)
    }
}, status=200)