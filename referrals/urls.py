from django.urls import path
from . import views

urlpatterns = [
    # Referral dashboard - shows user's referral stats and history
    path('dashboard/', views.referral_dashboard, name='referral_dashboard'),
    
    # Invite friend page - allows users to send referral invites via email
    path('invite/', views.invite_friend, name='invite_friend'),
]
