from django.urls import path
from applications import views

urlpatterns = [
    # Public and authentication-related URLs
    #path('register/', views.register, name='register'),
    path('thank-you/', views.thank_you, name='thank_you'),
    
    # User-specific URLs requiring login
    path('submit/', views.submit_application, name='apply'),
    path('status/', views.application_status, name='application_status'),
    path('application/<int:pk>/', views.application_details, name='application_details'),
    path('application/edit/<int:pk>/', views.edit_application, name='edit_application'),
    # Admin-only URLs
    path('admin/preview-email/<int:pk>/', views.preview_email, name='preview_email'),
    path('admin/resend-email/<int:pk>/', views.resend_email_view, name='resend_email'),
]