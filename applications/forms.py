from django import forms
from .models import ApplicantProfile, Application


class ApplicantProfileForm(forms.ModelForm):
    class Meta:
        model = ApplicantProfile
        fields = ['country', 'education_level', 'expertise_areas', 'portfolio_link']

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['resume', 'writing_sample', 'cover_letter', 'heard_about']
        widgets = {
            'heard_about': forms.Select(attrs={'class': 'form-select'}),
            'cover_letter': forms.Textarea(attrs={'rows': 5}),
    
        }

class RejectionReasonForm(forms.Form):
    """
    Form for providing a rejection reason when rejecting an application.
    """
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 50}),
        required=True,
        help_text="Please provide a reason for rejection that will be sent to the applicant."
    )
