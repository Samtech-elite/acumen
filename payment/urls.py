from django.urls import path
from django.views.generic import TemplateView
from .views import (
    PaymentUpdateView, 
    PaymentInitiateView, 
    PaymentProofUploadView, 
    PaymentVerificationView,
    verify_payment_ajax,
    initiate_stk_push_view
)

urlpatterns = [
    # Payment update view - handles payment processing for approved applications
    path('<int:application_id>/', PaymentUpdateView.as_view(), name='payment_update'),
    
    # Initiate payment view
    path('initiate/<int:application_id>/', PaymentInitiateView.as_view(), name='payment_initiate'),
    path('mpesa-stk-push/<int:application_id>/', initiate_stk_push_view, name='mpesa_stk_push'),
    # Payment proof upload view
    path('payment/<int:payment_id>/upload-proof/', PaymentProofUploadView.as_view(), name='payment_proof_upload'),
    
    # Payment verification view
    path('verify/<int:payment_id>/', PaymentVerificationView.as_view(), name='payment_verification'),
    
    # AJAX endpoint for verifying payment
    path('verify-ajax/<int:payment_id>/', verify_payment_ajax, name='verify_payment_ajax'),
    
    # Thank you page view
    path('thank-you/', TemplateView.as_view(template_name='payments/payment_thank_you.html'), name='payment_thank_you'),
]
