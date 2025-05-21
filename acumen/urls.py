from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    path('', include('users.urls')),
    path('referrals/', include('referrals.urls')),
    path('payment/', include('payment.urls')),
    path('applications/', include('applications.urls')),
    path('analytics/', include('analytics.urls')),
    path('admin/', admin.site.urls),
]
