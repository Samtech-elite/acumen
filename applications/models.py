from django.db import models
from django.conf import settings
from users.models import ApplicantProfile
import random
import string

def generate_reference_number():
    """
    Generate a unique 6-character reference number with a mixture of 
    capital letters and numbers
    """
    characters = string.ascii_uppercase + string.digits
    while True:
        # Generate a 6-character reference number
        reference = ''.join(random.choices(characters, k=6))
        
        # Check if this reference number already exists
        if not Application.objects.filter(reference_number=reference).exists():
            return reference


class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('interview', 'Interview Scheduled'),
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
    
    reference_number = models.CharField(
        max_length=100, 
        unique=True, 
        default=generate_reference_number,
        help_text="Unique reference number for this application"
    )
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
