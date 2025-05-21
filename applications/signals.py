from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Application
from .utils import send_application_email

@receiver(post_save, sender=Application)
def notify_application_status_change(sender, instance, created, **kwargs):
    if not created:  # Only send on update
        if instance.status == "approved":
            send_application_email(
                user=instance.applicant.user,
                status="approved",
                payment_url="https://acumenink.com/payment"  # or dynamically generate
            )
        elif instance.status == "rejected":
            send_application_email(
                user=instance.applicant.user,
                status="rejected",
                reason=instance.rejection_reason
            )
