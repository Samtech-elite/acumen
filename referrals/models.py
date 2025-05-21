from django.db import models
from django.conf import settings
import uuid

class ReferralCode(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='referral_code'
    )
    code = models.CharField(max_length=36, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Code: {self.code} - {self.user.email}"

class Referral(models.Model):
    STATUS_CHOICES = [
        ('invited', 'Invited'),
        ('registered', 'Registered'),
        ('applied', 'Applied'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    
    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='referrals_made'
    )
    referred_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='referred_by'
    )
    referred_email = models.EmailField(null=True, blank=True)
    referral_code = models.ForeignKey(ReferralCode, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='invited')
    
    # Timestamps for tracking referral progression
    invited_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('referrer', 'referred_user')
    
    def __str__(self):
        return f"{self.referrer.email} referred {self.referred_user.email}"
