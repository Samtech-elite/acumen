from django import forms
from .models import (
    Payment, 
    PayPalDetails,
    MpesaDetails,
    BankTransferDetails,
    CardPaymentDetails
)

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['method', 'confirmation_proof']
        widgets = {
            'method': forms.RadioSelect()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['confirmation_proof'].required = True
        self.fields['method'].widget.attrs.update({'class': 'payment-method-select'})
        

class PayPalDetailsForm(forms.ModelForm):
    class Meta:
        model = PayPalDetails
        fields = ['email', 'transaction_id']
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'PayPal account email'}),
            'transaction_id': forms.TextInput(attrs={'placeholder': 'Transaction ID (if available)'})
        }
        

class MpesaDetailsForm(forms.ModelForm):
    class Meta:
        model = MpesaDetails
        fields = ['phone_number', 'mpesa_code']
        widgets = {
            'phone_number': forms.TextInput(attrs={'placeholder': 'Phone number (e.g. +254712345678)'}),
            'mpesa_code': forms.TextInput(attrs={'placeholder': 'M-Pesa Confirmation Code'})
        }
        

class BankTransferDetailsForm(forms.ModelForm):
    class Meta:
        model = BankTransferDetails
        fields = ['account_name', 'bank_name', 'reference_number']
        widgets = {
            'account_name': forms.TextInput(attrs={'placeholder': 'Name on the sending account'}),
            'bank_name': forms.TextInput(attrs={'placeholder': 'Name of your bank'}),
            'reference_number': forms.TextInput(attrs={'placeholder': 'Bank transfer reference number'})
        }
        

class CardPaymentDetailsForm(forms.ModelForm):
    class Meta:
        model = CardPaymentDetails
        fields = ['card_type', 'last_four', 'cardholder_name', 'transaction_id']
        widgets = {
            'card_type': forms.Select(choices=[
                ('visa', 'Visa'),
                ('mastercard', 'Mastercard'),
                ('amex', 'American Express'),
                ('discover', 'Discover'),
                ('other', 'Other')
            ]),
            'last_four': forms.TextInput(attrs={
                'placeholder': 'Last 4 digits', 
                'maxlength': '4',
                'pattern': '[0-9]{4}',
                'title': 'Please enter exactly 4 digits'
            }),
            'cardholder_name': forms.TextInput(attrs={'placeholder': 'Name on the card'}),
            'transaction_id': forms.TextInput(attrs={'placeholder': 'Transaction ID (if available)'})
        }


def get_payment_details_form(payment_method):
    """Return the appropriate details form based on the payment method."""
    form_mapping = {
        'paypal': PayPalDetailsForm,
        'mpesa': MpesaDetailsForm,
        'bank_transfer': BankTransferDetailsForm,
        'card': CardPaymentDetailsForm,
    }
    return form_mapping.get(payment_method)


class CombinedPaymentForm:
    """
    Helper class to manage the combination of Payment form and the 
    appropriate payment details form based on the selected method.
    """
    def __init__(self, data=None, files=None, instance=None):
        self.payment_form = PaymentForm(data=data, files=files, instance=instance)
        self.details_form = None
        
        # If we have data and a valid payment method, create the details form
        if data and 'method' in data:
            payment_method = data.get('method')
            details_form_class = get_payment_details_form(payment_method)
            
            if details_form_class:
                # If we have an instance, try to get related details
                details_instance = None
                if instance and instance.pk:
                    try:
                        # This is a bit tricky as we need to get the right subclass
                        related_name = f"{payment_method}details"
                        if hasattr(instance, related_name):
                            details_instance = getattr(instance, related_name)
                    except Exception:
                        pass
                
                self.details_form = details_form_class(data=data, instance=details_instance)
    
    def is_valid(self):
        """Check if both forms are valid."""
        payment_valid = self.payment_form.is_valid()
        
        # If payment form is valid but no details form created yet, create it now
        if payment_valid and self.details_form is None:
            payment_method = self.payment_form.cleaned_data.get('method')
            details_form_class = get_payment_details_form(payment_method)
            if details_form_class:
                self.details_form = details_form_class()
                return False  # Need to submit details form
        
        # If we have a details form, check its validity
        details_valid = self.details_form is not None and self.details_form.is_valid()
        
        return payment_valid and details_valid
    
    def save(self):
        """Save both forms and establish the relationship between them."""
        if not self.is_valid():
            raise ValueError("Forms must be valid before saving")
        
        # Save payment first
        payment = self.payment_form.save()
        
        # Save details and link to payment
        if self.details_form:
            details = self.details_form.save(commit=False)
            details.payment = payment
            details.save()
        
        return payment
