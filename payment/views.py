from django.views.generic import UpdateView, FormView, TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse

from applications.models import Application
from .models import Payment
from .forms import PaymentForm, CombinedPaymentForm
from .utils import verify_payment_confirmation  # OCR helper function
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from payment.api import initiate_stk_push  # Assuming this is the function to call PayHero API
import uuid
from payment.models import PaymentLog  # Assuming you have a model to log payment actions







@login_required
@csrf_exempt
def initiate_stk_push_view(request, application_id):
    """Handles the AJAX request to initiate STK push."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    application = get_object_or_404(Application, id=application_id)
    user = request.user
    
    # Handle both JSON and form data
    if request.content_type == 'application/json':
        import json
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
    else:
        phone_number = request.POST.get('phone_number')

    if not phone_number:
        return JsonResponse({'success': False, 'message': 'Phone number is required.'}, status=400)

    if not (phone_number.startswith('2547') or phone_number.startswith('2541')) or len(phone_number) != 12:
        if phone_number.startswith('07') and len(phone_number) == 10:
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('01') and len(phone_number) == 10:
            phone_number = '254' + phone_number[1:]
        else:
            return JsonResponse({'success': False, 'message': 'Invalid phone number format. Use 2547XXXXXXXX or 2541XXXXXXXX.'}, status=400)

    external_reference = f"APPLICATION_{application.id}_{user.id}_{uuid.uuid4().hex[:8]}"

    # Make sure the amount is properly passed to the API function
    amount = application.amount if hasattr(application, 'amount') else 25  # Default value if application doesn't have amount
    
    api_response = initiate_stk_push(phone_number, amount, external_reference)

    if api_response.get("success"):
        payhero_reference = api_response.get("transaction_id") 
        Payment.objects.create(
            user=user,
            application=application,
            amount=amount,
            status='completed',
            payment_method='mpesa_stk',
            phone_number=phone_number,
            merchant_reference=payhero_reference, 
            internal_reference=application.reference_number 
        )
        
        return JsonResponse({'success': True, 'transaction_id': payhero_reference, 'message': 'STK push initiated.'})
    else:
        return JsonResponse({'success': False, 'message': api_response.get("message", "Failed to initiate STK push.")}, status=400)
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
            'amount': 25,  # should be set dynamically elsewhere
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


class PaymentInitiateView(FormView):
    """View for initiating a payment with payment details"""
    template_name = 'payments/payment_initiate.html'
    form_class = CombinedPaymentForm
    
    def form_valid(self, form):
        payment = form.save()
        self.payment = payment
        
        # Check if method is card payment - redirect to payment gateway
        if payment.method == 'card':
            # If we have card details with checkout URL, redirect there
            if hasattr(payment, 'card_details') and payment.card_details.company_card_checkout_url:
                return redirect(payment.card_details.company_card_checkout_url)
        
        # For all other methods, redirect to confirmation upload page
        messages.success(self.request, "Payment details saved. Please upload your payment confirmation.")
        return super().form_valid(form)
    
    def get_success_url(self):
        # Redirect to the payment confirmation upload page
        return reverse('payment_proof_upload', kwargs={'payment_id': self.payment.id})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        app_id = self.kwargs.get('application_id')
        application = get_object_or_404(Application, id=app_id, status='approved')
        
        # Get or create payment
        payment, created = Payment.objects.get_or_create(
            application=application, 
            defaults={
                'method': 'paypal',
                'amount': 25,
                'currency': 'USD'
            }
        )
        
        kwargs['instance'] = payment
        return kwargs
    
    def form_valid(self, form):
        payment = form.save()
        self.payment = payment
        messages.success(self.request, "Payment details saved successfully. Please upload your payment confirmation.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('payment_proof_upload', kwargs={'payment_id': self.payment.id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        app_id = self.kwargs.get('application_id')
        application = get_object_or_404(Application, id=app_id)
        payment, _ = Payment.objects.get_or_create(application=application)
        
        context.update({
            'application': application,
            'payment': payment,
            'support_email': 'support@acumenink.com'
        })
        return context



class PaymentProofUploadView(UpdateView):
    """View for uploading payment confirmation proof"""
    model = Payment
    template_name = 'payments/payment_proof_upload.html'
    form_class = PaymentForm
    pk_url_kwarg = 'payment_id'
    
    def get_queryset(self):
        # Ensure users can only upload proof for their own payments
        return Payment.objects.filter(application__applicant__user=self.request.user)
    
    def form_valid(self, form):
        payment = form.save(commit=False)
        
        # Update payment status if proof is uploaded
        if payment.confirmation_proof:
            payment.status = 'pending'  # Change to pending verification
            
            # Create a log entry
            PaymentLog.objects.create(
                payment=payment,
                action='proof_uploaded',
                performed_by=self.request.user,
                notes='Payment proof uploaded by user'
            )
            
            messages.success(self.request, "Payment proof uploaded successfully. Your payment is now pending verification.")
        
        payment.save()
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('payment_thank_you')


class PaymentVerificationView(TemplateView):
    """View for verifying payment with loading animation"""
    template_name = 'payments/payment_verification.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_id = self.kwargs.get('payment_id')
        payment = get_object_or_404(Payment, id=payment_id)
        
        context.update({
            'payment': payment,
            'support_email': 'support@acumenink.com'
        })
        return context


def verify_payment_ajax(request, payment_id):
    """AJAX endpoint for verifying payment confirmation"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Check if confirmation proof exists
    if not payment.confirmation_proof:
        return JsonResponse({
            'success': False,
            'error': 'No payment confirmation uploaded',
            'redirect': None
        })
    
    try:
        file_path = payment.confirmation_proof.path
        expected_amount = payment.amount
        payment_method_name = payment.get_method_display()
        
        success, error_msg = verify_payment_confirmation(file_path, expected_amount, payment_method_name)
        
        if success:
            payment.confirmation_verified = True
            payment.status = 'verified'
            payment.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Payment confirmation verified successfully',
                'redirect': reverse_lazy('payment_thank_you')
            })
        else:
            payment.confirmation_verified = False
            payment.status = 'pending'  # keep pending to allow retry
            payment.save()
            
            return JsonResponse({
                'success': False,
                'error': f"Verification failed: {error_msg} Please upload a clearer image.",
                'redirect': reverse_lazy('payment_proof_upload', kwargs={'payment_id': payment.id})
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Payment verification failed. Payment not found or invalid format.',
            'redirect': None
        })
