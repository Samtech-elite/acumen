from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser, ApplicantProfile
from django_countries.widgets import CountrySelectWidget

class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your first name'})
    )
    last_name = forms.CharField(
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your last name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email address'})
    )
    
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Username is automatically set to email in the model's save method
        if commit:
            user.save()
        return user

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Email',
        widget=forms.TextInput(attrs={'placeholder': 'Enter your email'})
    )

class ResendVerificationForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Enter your email'}))

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
        }

class ProfileUpdateForm(forms.ModelForm):
    EDUCATION_CHOICES = [
        ('', 'Select your education level'),
        ('high_school', 'High School'),
        ('bachelors', 'Bachelor\'s Degree'),
        ('masters', 'Master\'s Degree'),
        ('phd', 'PhD'),
        ('other', 'Other')
    ]
    
    education_level = forms.ChoiceField(
        choices=EDUCATION_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
        })
    )
    
    portfolio_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
            'accept': '.pdf,.doc,.docx'
        })
    )

    class Meta:
        model = ApplicantProfile
        fields = ['country', 'education', 'education_level', 'expertise_areas', 'portfolio_link', 'portfolio_file']
        widgets = {
            'country': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
            'education': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'rows': 3,
                'placeholder': 'Additional details about your education'
            }),
            'expertise_areas': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'rows': 3,
                'placeholder': 'List up to 5 expertise areas separated by commas (e.g., Technical Writing, Content Marketing, SEO)'
            }),
            'portfolio_link': forms.URLInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Enter your portfolio URL (optional if uploading file)'
            }),
        }
        
    def clean_expertise_areas(self):
        expertise = self.cleaned_data.get('expertise_areas', '')
        if expertise:
            areas = [area.strip() for area in expertise.split(',') if area.strip()]
            if len(areas) > 5:
                raise forms.ValidationError("Please enter no more than 5 expertise areas.")
            return ', '.join(areas)
        return expertise
        
    def clean(self):
        cleaned_data = super().clean()
        portfolio_link = cleaned_data.get('portfolio_link')
        portfolio_file = cleaned_data.get('portfolio_file')
        
        if not portfolio_link and not portfolio_file:
            self.add_error(None, "Please provide either a portfolio URL or upload a file.")
        
        return cleaned_data
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # Save the education level to the profile
        if self.cleaned_data.get('education_level'):
            profile.education_level = self.cleaned_data['education_level']
            
        # Handle the portfolio file if provided
        if self.cleaned_data.get('portfolio_file'):
            # The actual file handling would be implemented in the view
            # This is just a placeholder to acknowledge we received a file
            profile.has_portfolio_file = True
            
        if commit:
            profile.save()
        return profile

