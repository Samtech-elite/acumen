from django.views.generic import UpdateView
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages

from applications.models import Application
from .models import Payment
from .forms import PaymentForm
from .utils import verify_payment_confirmation  # OCR helper function


class PaymentUpdateView(UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'payments/payment_form.html'

    def get_object(self, queryset=None):
        app_id = self.kwargs.get('application_id')
        application = get_object_or_404(Application, id=app_id, status='approved')

        # Create or get the Payment object for this application
        payment, created = Payment.objects.get_or_create(application=application, defaults={
            'method': 'paypal',  # default payment method, can be changed
            'amount': 0,  # should be set dynamically elsewhere
            'currency': 'USD'  # default currency, could be customized per user
        })

        return payment

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # Dynamically filter payment method choices based on applicant country
        applicant_country = self.get_object().application.applicant.country.lower()

        allowed_methods = ['paypal', 'bank_transfer', 'card']
        if applicant_country == 'kenya':
            allowed_methods.append('mpesa')

        form.fields['method'].choices = [
            (key, label) for key, label in Payment.PAYMENT_METHOD_CHOICES if key in allowed_methods
        ]

        return form

    def form_valid(self, form):
        response = super().form_valid(form)
        payment = form.instance

        # Run OCR verification on uploaded confirmation
        file_path = payment.confirmation_proof.path
        expected_amount = payment.amount
        payment_method_name = payment.get_method_display()

        success, error_msg = verify_payment_confirmation(file_path, expected_amount, payment_method_name)

        if success:
            payment.confirmation_verified = True
            payment.status = 'verified'
            payment.save()
            messages.success(self.request, "Payment confirmation verified successfully.")
        else:
            payment.confirmation_verified = False
            payment.status = 'pending'  # keep pending to allow retry
            payment.save()
            messages.error(self.request, f"Verification failed: {error_msg} Please upload a clearer image.")

        return response

    def get_success_url(self):
        return reverse_lazy('payment_thank_you')  # Make sure this URL/view exists
