from django.urls import path
from . import views

urlpatterns = [
    # Payment update view - handles payment processing for approved applications
    path('application/<int:application_id>/payment/', views.PaymentUpdateView.as_view(), name='payment_update'),
    
    # Note: You need to create a thank you view or use a TemplateView for this URL
]
