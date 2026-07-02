from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.customers.models import RiderProfile
from apps.ratings.models import Rating
from apps.trips.models import Trip

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a sample completed trip and ratings for a test rider'

    def handle(self, *args, **options):
        user = User.objects.filter(username='john_doe').first() or User.objects.create_user(
            username='john_doe',
            email='john_doe@example.com',
            password='StrongPass123!',
        )

        RiderProfile.objects.get_or_create(user=user)
        driver = User.objects.filter(username='driver1').first() or User.objects.create_user(
            username='driver1',
            email='driver1@example.com',
            password='StrongPass123!',
        )

        trip = Trip.objects.create(
            rider=user,
            driver=driver,
            pickup_address='Outer Ring Road, Bengaluru',
            pickup_latitude='12.934533',
            pickup_longitude='77.695814',
            drop_address='Indiranagar, Bengaluru',
            drop_latitude='12.971598',
            drop_longitude='77.641267',
            status=Trip.Status.COMPLETED,
            fare='182.50',
            distance_km='8.40',
            requested_at=timezone.now().replace(hour=10, minute=0, second=0, microsecond=0),
            completed_at=timezone.now().replace(hour=10, minute=25, second=0, microsecond=0),
        )

        Rating.objects.get_or_create(
            trip=trip,
            given_by_rider=user,
            defaults={'score': '4.5', 'comment': 'Great ride'}
        )
        Rating.objects.get_or_create(
            trip=trip,
            given_by_rider=driver,
            defaults={'score': '5.0', 'comment': 'Very courteous rider'}
        )

        self.stdout.write(self.style.SUCCESS(f'Created sample trip {trip.pk} with ratings'))
