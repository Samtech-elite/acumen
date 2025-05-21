from django.db import models
from django.conf import settings
from users.models import ApplicantProfile
class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    EMAIL_STATUS_CHOICES = [
        ('none', 'None'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    HEARD_ABOUT_CHOICES = [
        ('social_media', 'Social Media'),
        ('referral', 'Referral'),
        ('search_engine', 'Search Engine'),
        ('other', 'Other'),
    ]

    applicant = models.ForeignKey(ApplicantProfile, on_delete=models.CASCADE)
    resume = models.FileField(upload_to='resumes/')
    writing_sample = models.FileField(upload_to='writing_samples/')
    cover_letter = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)

    # Email tracking
    email_status = models.CharField(max_length=20, choices=EMAIL_STATUS_CHOICES, default='none')
    email_last_sent_at = models.DateTimeField(null=True, blank=True)

    # Marketing source
    heard_about = models.CharField(max_length=50, choices=HEARD_ABOUT_CHOICES, blank=True, null=True)
    previous_application = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resubmissions',
        help_text="Optional: Link to a previous application if this is a resubmission."
    )

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Application by {self.applicant.user.email} - {self.status}"


class ApplicationLog(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=50)  # e.g., 'approved', 'rejected', 'edited'
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} by {self.admin} at {self.timestamp}"
