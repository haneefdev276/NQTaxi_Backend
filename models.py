from django.db import models  #imports Django Databases tools


class Fare(models.Model):  #model = python class that represents a database table
    RIDE_TYPES = [
        ('bike', 'Bike'),
        ('auto', 'Auto'),
        ('car', 'Car'),
    ]

    ride_type = models.CharField(   #stores ride types as text
        max_length=10,
        choices=RIDE_TYPES,
        unique=True
    )

    base_fare = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    per_km_fare = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    per_minute_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    def __str__(self):   #controls how the object appears in django admin ( objects(1) = bike )
        return self.ride_type