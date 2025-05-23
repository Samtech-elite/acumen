from django import forms
from users.models import CustomUser as  User
from .models import Referral

class ReferralInviteForm(forms.Form):
    referred_email = forms.EmailField(
        label="Friend's Email Address",
        max_length=254,
        widget=forms.EmailInput(attrs={'placeholder': "Enter friend's email"})
    )

    def __init__(self, *args, **kwargs):
        self.referrer = kwargs.pop('referrer', None)
        super().__init__(*args, **kwargs)

    def clean_referred_email(self):
        email = self.cleaned_data['referred_email'].lower()

        # Prevent inviting oneself
        if self.referrer and self.referrer.email.lower() == email:
            raise forms.ValidationError("You cannot invite yourself.")

        # Check if this email is already invited by this referrer
        if Referral.objects.filter(referrer=self.referrer, referred_email=email).exists():
            raise forms.ValidationError("You have already invited this email.")

        # Optional: check if email belongs to an existing registered user
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This user has already registered.")

        return email
