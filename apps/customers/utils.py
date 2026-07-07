from apps.customers.models import RiderProfile


def get_rider_profile(user):
    profile, _ = RiderProfile.objects.get_or_create(user=user)
    return profile
