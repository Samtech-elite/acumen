from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, ApplicantProfile

@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Create or update user profile when a user is created or updated."""
    if created:
        ApplicantProfile.objects.create(user=instance)
    else:
        # Try to get the profile, create if it doesn't exist
        ApplicantProfile.objects.get_or_create(user=instance)
