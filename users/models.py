from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django_countries.fields import CountryField
from django.conf import settings

class CustomUserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier
    for authentication instead of username.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email_verified = models.BooleanField(default=False)
    verification_sent_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = CustomUserManager()
    
    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        # Set username to email if not explicitly provided
        if not self.username or self.username != self.email:
            self.username = self.email
        super().save(*args, **kwargs)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

class ApplicantProfile(models.Model):
    EDUCATION_CHOICES = [
        ('high_school', 'High School'),
        ('bachelors', 'Bachelor\'s Degree'),
        ('masters', 'Master\'s Degree'),
        ('phd', 'PhD'),
        ('other', 'Other')
    ]
    
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='user_profile'
    )
    country = CountryField(blank_label='(Select country)')
    education = models.TextField(blank=True)
    education_level = models.CharField(
        max_length=20,
        choices=EDUCATION_CHOICES,
        default=''
    )
    expertise_areas = models.TextField(help_text="List up to 5 writing expertise areas separated by commas")
    portfolio_link = models.URLField(blank=True, null=True)
    portfolio_file = models.FileField(upload_to='portfolios/', blank=True, null=True)
    has_portfolio_file = models.BooleanField(default=False)
    last_active = models.DateTimeField(auto_now=True)  # for tracking

    def __str__(self):
        return self.user.email or self.user.username








