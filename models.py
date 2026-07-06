from django.db import models

class Payment(models.Model):
    booking_id = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    razopay_order_id = models.CharField(max_length=255,blank=True)
    razopay_payment_id = models.CharField(max_length=255,blank=True)
    status = models.CharField(max_length=20,default="pending")
    created_at =models.DateTimeField(auto_now_add=True)
