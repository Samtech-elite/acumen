# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string

from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomUser, ApplicantProfile
from .forms import (
    RegistrationForm, LoginForm, ResendVerificationForm,
    UserUpdateForm, ProfileUpdateForm
)
# Import these models or adjust the dashboard view if they're from another app
from applications.models import Application
from payment.models import Payment
from django.views import View
from django.core.mail import EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from referrals.models import ReferralCode
from django.contrib.auth import logout
def home(request):
    return render(request,'home.html')

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            print('Form is valid')
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            ApplicantProfile.objects.create(user=user)
              
            ReferralCode.objects.create(user=user)
            current_site = get_current_site(request)
            subject = 'Verify Your email'
            message = render_to_string('users/activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            email = EmailMessage(
                subject,
                message,
                'samtech.websites@gmail.com',
                [user.email],
            )
            email.content_subtype = "html"
            email.send()
            messages.success(request, 'Account created. Please check your email to verify your account.')
            return redirect('activation_sent')
        else:
            print('Form is not valid', form.errors)
            messages.error(request, 'Please correct the errors below.')
    else:
        print('Not a POST request')
        form = RegistrationForm()
    return render(request, 'users/register.html', {'form': form})


def activation_sent(request):
    #tutor = request.user
    return render(request, 'users/activation_sent.html')

def activation_invalid(request):
    return render(request, 'users/activation_invalid.html')

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.email_confirmed = True
        user.save()
        login(request, user)
        return redirect('profile_update')  # Redirect to a page after activation
    else:
        return render(request, 'users/activation_invalid.html')
def logout_view(request):
    logout(request)
    return redirect('home')

def application_waiting(request):
    return render(request, 'applications/waiting.html')

def application_approved(request):
    return render(request, 'applications/approved.html')

def application_rejected(request):
    return render(request, 'applications/rejected.html')

def send_verification_email(request, user):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = request.build_absolute_uri(reverse('activate', kwargs={'uidb64': uid, 'token': token}))
    subject = 'Verify Your Email'
    message = render_to_string('emails/email_verification.html', {'user': user, 'link': link})
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
    user.verification_sent_at = timezone.now()
    user.save()

def token_expired(request):
    email = request.session.get('resend_email')
    return render(request, 'users/token_expired.html', {'email': email})


def resend_verification(request):
    if request.method == 'POST':
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = CustomUser.objects.get(email=email)
                if not user.email_verified:
                    send_verification_email(request, user)
                    messages.success(request, 'A new verification email has been sent.')
                else:
                    messages.info(request, 'Your email is already verified.')
            except CustomUser.DoesNotExist:
                messages.error(request, 'No account found with that email.')
            return redirect('register')
    else:
        form = ResendVerificationForm(initial={'email': request.GET.get('email', '')})
    return render(request, 'emails/resend_email.html', {'form': form})


@login_required
def profile_update(request):
    # Ensure user has a profile
    try:
        profile = ApplicantProfile.objects.get(user=request.user)
    except ApplicantProfile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = ApplicantProfile.objects.create(user=request.user)
   
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(
            request.POST, 
            request.FILES,  # Add this line to handle file uploads
            instance=profile
        )

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            profile_instance = p_form.save(commit=False)
            
            # Handle file upload if provided
            if 'portfolio_file' in request.FILES:
                profile_instance.portfolio_file = request.FILES['portfolio_file']
                profile_instance.has_portfolio_file = True
                
            profile_instance.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('apply')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile)

    return render(request, 'users/profile.html', {
        'u_form': u_form,
        'p_form': p_form
    })


@login_required
def user_dashboard(request):
    profile = ApplicantProfile.objects.get(user=request.user)
    if not profile:
        # If the profile doesn't exist, create it
        profile = ApplicantProfile.objects.create(user=request.user)
    
    applications = Application.objects.filter(applicant=profile)
    payments = Payment.objects.filter(application__applicant=profile)

    return render(request, 'users/dashboard.html', {
        'profile': profile,
        'applications': applications,
        'payments': payments
    })

class LoginView(View):
    template_name = 'users/login.html'
    
    def get(self, request):
        # If user is already authenticated, redirect to dashboard
        if request.user.is_authenticated:
            return redirect('dashboard')  # Replace with your dashboard URL name
        return render(request, self.template_name)
    
    def post(self, request):
        # Get form data
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        if not email or not password:
            messages.error(request, 'Please provide both email and password')
            return render(request, self.template_name)
        
        # Authenticate user - since email is the USERNAME_FIELD, we pass it as username
        user = authenticate(username=email, password=password)
        
        if user is not None:
            # Check if email is verified (if your app requires email verification)
            if hasattr(user, 'email_verified') and not user.email_verified:
                messages.warning(
                    request, 
                    'Please verify your email before logging in. '
                    'Check your inbox or <a href="/resend-verification/">resend verification email</a>.'
                )
                return render(request, self.template_name)
            
            # Login the user
            login(request, user)
            
            # Set session expiry based on remember_me checkbox
            if not remember_me:
                # Session will expire when the user closes their browser
                request.session.set_expiry(0)
            else:
                # Session will expire after 2 weeks (in seconds)
                request.session.set_expiry(60 * 60 * 24 * 14)
            
            # Redirect user after successful login
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')  # Replace with your dashboard URL name
        else:
            # Authentication failed
            messages.error(request, 'Invalid email or password')
            return render(request, self.template_name)


