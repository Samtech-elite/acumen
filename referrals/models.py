from django.db import models
from django.conf import settings
import random
import string
from django.urls import reverse
from django.contrib.sites.models import Site

def generate_referral_code():
    """
    Generate a unique 4-character referral code with a mixture of 
    capital letters and numbers
    """
    characters = string.ascii_uppercase + string.digits
    while True:
        # Generate a 4-character referral code
        code = ''.join(random.choices(characters, k=4))
        
        # Check if this code already exists
        if not ReferralCode.objects.filter(code=code).exists():
            return code


class ReferralCode(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='referral_code'
    )
    code = models.CharField(max_length=4, unique=True, default=generate_referral_code)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Code: {self.code} - {self.user.email}"
    
    def get_referral_link(self):
        """Generate a full URL for this referral code"""
        # Get the current site domain
        current_site = Site.objects.get_current()
        # Build the absolute URL to the registration page with the referral code
        path = reverse('register') + f'?ref={self.code}'
        return f"https://{current_site.domain}{path}"


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
        related_name='referred_by',
        blank=True,
        null=True
    )
    referred_email = models.EmailField(null=True, blank=True)
    referral_code = models.ForeignKey(
        ReferralCode, 
        on_delete=models.SET_NULL,  # Changed from CASCADE to SET_NULL for better data integrity
        related_name='referrals', 
        null=True, 
        blank=True
    )
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
