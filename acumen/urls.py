from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('users.urls')),
    path('referrals/', include('referrals.urls')),
    path('payment/', include('payment.urls')),
    path('applications/', include('applications.urls')),
    path('sam/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
