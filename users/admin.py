from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, ApplicantProfile
from django.urls import reverse
from django.utils.html import format_html


class ApplicantProfileInline(admin.StackedInline):
    model = ApplicantProfile
    can_delete = False
    verbose_name_plural = 'Applicant Profile'
    fk_name = 'user'


class CustomUserAdmin(UserAdmin):
    """Admin interface for CustomUser model."""
    ordering = ('-date_joined',)
    list_display = ('first_name', 'last_name', 'is_active', 'is_staff', 
                   'is_verified', 'date_joined', 'get_country', 'has_application')
    list_filter = ('is_staff', 'is_active', 'is_verified', 'user_profile__country')
    search_fields = ('email', 'first_name', 'last_name')
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Verification'), {'fields': ('is_verified', 'email_verified', 'verification_sent_at')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    
    inlines = (ApplicantProfileInline,)
    
    def get_country(self, obj):
        try:
            return obj.user_profile.country.name
        except (ApplicantProfile.DoesNotExist, AttributeError):
            return '-'
    get_country.short_description = 'Country'
    get_country.admin_order_field = 'user_profile__country'
    
    def has_application(self, obj):
        try:
            if hasattr(obj.user_profile, 'applications') and obj.user_profile.applications.exists():
                app = obj.user_profile.applications.latest('submitted_at')
                url = reverse('admin:applications_application_change', args=[app.pk])
                return format_html('<a href="{}">{}</a>', url, app.get_status_display())
            return '-'
        except Exception:
            return '-'
    has_application.short_description = 'Application'
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


@admin.register(ApplicantProfile)
class ApplicantProfileAdmin(admin.ModelAdmin):
    """Admin interface for ApplicantProfile model."""
    list_display = ('user', 'country', 'expertise_areas', 'last_active')
    list_filter = ('country', 'last_active')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'expertise_areas')
    raw_id_fields = ('user',)
    
    fieldsets = (
        (None, {
            'fields': ('user',)
        }),
        (_('Profile Information'), {
            'fields': ('country', 'education', 'expertise_areas', 'portfolio_link')
        }),
        (_('Activity'), {
            'fields': ('last_active',)
        }),
    )
    
    readonly_fields = ('last_active',)
    
    def get_queryset(self, request):
        """Prefetch related user data to improve performance."""
        return super().get_queryset(request).select_related('user')
    
    def has_add_permission(self, request):
        """Prevent adding profiles directly - they should be created with users."""
        return False


# Register the custom admin classes
admin.site.register(CustomUser, CustomUserAdmin)
