from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import Payment

@admin.action(description="Mark selected payments as Approved")
def make_approved(modeladmin, request, queryset):
    updated = queryset.update(status='approved')
    modeladmin.message_user(request, f"{updated} payments marked as Approved.")

@admin.action(description="Mark selected payments as Rejected")
def make_rejected(modeladmin, request, queryset):
    updated = queryset.update(status='rejected')
    modeladmin.message_user(request, f"{updated} payments marked as Rejected.")

class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'application_link',
        'method',
        'amount',
        'colored_status',
        'confirmation_preview',
        'submitted_at',
        'updated_at',
    )
    list_filter = ('status', 'method', 'submitted_at')
    search_fields = ('application__applicant__user__username', 'application__applicant__user__email')
    readonly_fields = ('confirmation_preview', 'submitted_at', 'updated_at')

    actions = [make_approved, make_rejected]

    def application_link(self, obj):
        url = f"/admin/applications/application/{obj.application.id}/change/"
        return format_html('<a href="{}">Application #{}</a>', url, obj.application.id)
    application_link.short_description = 'Application'

    def confirmation_preview(self, obj):
        if obj.confirmation_proof:
            return format_html('<img src="{}" style="max-height:100px; max-width:150px;" />', obj.confirmation_proof.url)
        return "No image"
    confirmation_preview.short_description = 'Payment Proof'

    def colored_status(self, obj):
        color_map = {
            'pending': 'orange',
            'verified': 'blue',
            'approved': 'green',
            'rejected': 'red',
        }
        color = color_map.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};"><strong>{}</strong></span>',
            color,
            obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'

    def changelist_view(self, request, extra_context=None):
        totals = Payment.objects.values('status').annotate(total=Sum('amount'))
        status_totals = {status: 0 for status, _ in Payment.STATUS_CHOICES}
        for entry in totals:
            status_totals[entry['status']] = entry['total'] or 0
        if extra_context is None:
            extra_context = {}
        extra_context['status_totals'] = status_totals
        return super().changelist_view(request, extra_context=extra_context)

admin.site.register(Payment, PaymentAdmin)
