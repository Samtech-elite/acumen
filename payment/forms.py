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
    def __init__(self, data=None, files=None, instance=None, initial=None, prefix=None):
        # Accept all standard form parameters, including initial
        self.payment_form = PaymentForm(
            data=data, 
            files=files, 
            instance=instance,
            initial=initial,
            prefix=prefix
        )
        self.details_form = None
        self.instance = instance
        
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
                
                details_initial = None
                if initial and f'{payment_method}_details' in initial:
                    details_initial = initial[f'{payment_method}_details']
                
                self.details_form = details_form_class(
                    data=data, 
                    instance=details_instance,
                    initial=details_initial,
                    prefix=f"{payment_method}_details" if prefix else None
                )
        # If we have an instance with a method but no POST data (initial GET request)
        elif instance and instance.pk and instance.method:
            payment_method = instance.method
            details_form_class = get_payment_details_form(payment_method)
            
            if details_form_class:
                details_instance = None
                try:
                    related_name = f"{payment_method}details"
                    if hasattr(instance, related_name):
                        details_instance = getattr(instance, related_name)
                except Exception:
                    pass
                
                details_initial = None
                if initial and f'{payment_method}_details' in initial:
                    details_initial = initial[f'{payment_method}_details']
                
                self.details_form = details_form_class(
                    instance=details_instance,
                    initial=details_initial,
                    prefix=f"{payment_method}_details" if prefix else None
                )
    
    
    def is_valid(self):
        """
        Validate both the payment form and details form (if present)
        """
        payment_valid = self.payment_form.is_valid()
        
        # If payment form is valid and we have a details form, validate it too
        if payment_valid and self.details_form:
            details_valid = self.details_form.is_valid()
            return payment_valid and details_valid
        
        # If we don't have a details form (or payment form is invalid), just return payment form validity
        return payment_valid
    
    def save(self, commit=True):
        """
        Save both the payment form and the details form
        """
        # Save the payment form first
        payment = self.payment_form.save(commit=commit)
        
        # If we have a details form, save it and link to the payment
        if self.details_form and self.details_form.has_changed():
            details = self.details_form.save(commit=False)
            details.payment = payment
            
            if commit:
                details.save()
                
                # If we changed payment method, remove any old details objects
                # that might be associated with this payment
                if payment.method:
                    for method_name in ['paypal', 'mpesa', 'bank_transfer', 'card']:
                        if method_name != payment.method:
                            related_name = f"{method_name}details"
                            if hasattr(payment, related_name):
                                try:
                                    old_details = getattr(payment, related_name)
                                    old_details.delete()
                                except Exception:
                                    pass
    
        return payment
    
    def has_changed(self):
        """
        Return True if data differs from initial.
        """
        payment_changed = self.payment_form.has_changed()
        if self.details_form:
            details_changed = self.details_form.has_changed()
            return payment_changed or details_changed
        return payment_changed
    
    @property
    def errors(self):
        """
        Return errors from both forms
        """
        payment_errors = self.payment_form.errors
        if self.details_form:
            details_errors = self.details_form.errors
            if details_errors:
                return {**payment_errors, **details_errors}
        return payment_errors
