from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Registration and account verification
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('activation_sent/', views.activation_sent, name='activation_sent'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    path('token-expired/', views.token_expired, name='token_expired'),
    
    # Authentication
    path('accounts/login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
        # User profiles and dashboard
    path('profile/', views.profile_update, name='profile_update'),
    path('dashboard/', views.user_dashboard, name='dashboard'),
    # Password management
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='users/password_reset.html'), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), 
         name='password_reset_complete'),
    path('application/waiting/', views.application_waiting, name='application_waiting'),
    path('application/approved/', views.application_approved, name='application_approved'),
    path('application/rejected/', views.application_rejected, name='application_rejected'),

]
