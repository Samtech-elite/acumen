from django.contrib import admin
from .models import Referral, ReferralCode


@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at')
    search_fields = ('user__email', 'code')
    readonly_fields = ('created_at',)


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer_email', 'referred_user_email', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('referrer__email', 'referred_user__email', 'referral_code__code')
    readonly_fields = ('created_at',)
    
    def referrer_email(self, obj):
        return obj.referrer.email
    referrer_email.short_description = "Referrer"
    
    def referred_user_email(self, obj):
        return obj.referred_user.email
    referred_user_email.short_description = "Referred User"
