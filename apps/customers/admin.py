from django.contrib import admin

from apps.customers.models import EmergencyContact, PaymentMethod, RiderProfile, SavedPlace

admin.site.register(RiderProfile)
admin.site.register(PaymentMethod)
admin.site.register(SavedPlace)
admin.site.register(EmergencyContact)
