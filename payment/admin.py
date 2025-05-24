from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Payment, 
    PayPalDetails, 
    MpesaDetails, 
    BankTransferDetails, 
    CardPaymentDetails,
    PaymentLog
)


class PaymentLogInline(admin.TabularInline):
    model = PaymentLog
    extra = 0
    readonly_fields = ('action', 'performed_by', 'notes', 'timestamp')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class PayPalDetailsInline(admin.StackedInline):
    model = PayPalDetails
    can_delete = False
    verbose_name = "PayPal Details"
    verbose_name_plural = "PayPal Details"


class MpesaDetailsInline(admin.StackedInline):
    model = MpesaDetails
    can_delete = False
    verbose_name = "M-Pesa Details"
    verbose_name_plural = "M-Pesa Details"


class BankTransferDetailsInline(admin.StackedInline):
    model = BankTransferDetails
    can_delete = False
    verbose_name = "Bank Transfer Details"
    verbose_name_plural = "Bank Transfer Details"


class CardPaymentDetailsInline(admin.StackedInline):
    model = CardPaymentDetails
    can_delete = False
    verbose_name = "Card Payment Details"
    verbose_name_plural = "Card Payment Details"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'application_link', 'method', 'amount', 'currency', 'status', 
                    'confirmation_verified', 'submitted_at', 'view_confirmation')
    list_filter = ('method', 'status', 'confirmation_verified', 'currency')
    search_fields = ('application__reference_number', 'application__applicant__email')
    readonly_fields = ('submitted_at', 'updated_at', 'confirmation_image')
    date_hierarchy = 'submitted_at'
    
    fieldsets = (
        ('Application Information', {
            'fields': ('application',)
        }),
        ('Payment Information', {
            'fields': ('method', 'amount', 'currency', 'status')
        }),
        ('Confirmation', {
            'fields': ('confirmation_proof', 'confirmation_image', 'confirmation_verified', 'retry_allowed')
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def application_link(self, obj):
        """Return a link to the application admin page"""
        if obj.application:
            url = f"/admin/applications/application/{obj.application.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.reference_number)
        return "-"
    application_link.short_description = "Application"
    
    def confirmation_image(self, obj):
        """Display the confirmation image in the admin"""
        if obj.confirmation_proof:
            return format_html('<img src="{}" style="max-height: 300px;" />', obj.confirmation_proof.url)
        return "No image uploaded"
    confirmation_image.short_description = "Confirmation Image Preview"
    
    def view_confirmation(self, obj):
        """Provide a link to view the confirmation"""
        if obj.confirmation_proof:
            return format_html('<a href="{}" target="_blank">View</a>', obj.confirmation_proof.url)
        return "-"
    view_confirmation.short_description = "View Proof"
    
    def get_inlines(self, request, obj=None):
        """Dynamically show only the relevant payment details inline based on the payment method"""
        if not obj:
            return [PaymentLogInline]
            
        inlines = [PaymentLogInline]
        
        # Add the appropriate details inline based on the payment method
        if obj.method == 'paypal':
            inlines.append(PayPalDetailsInline)
        elif obj.method == 'mpesa':
            inlines.append(MpesaDetailsInline)
        elif obj.method == 'bank_transfer':
            inlines.append(BankTransferDetailsInline)
        elif obj.method == 'card':
            inlines.append(CardPaymentDetailsInline)
            
        return inlines
    
    def save_model(self, request, obj, form, change):
        """Log changes when an admin updates a payment"""
        is_new = not obj.pk
        original_status = None
        
        # Get the original status if this is an update
        if not is_new:
            original = Payment.objects.get(pk=obj.pk)
            original_status = original.status
        
        # Save the payment object
        super().save_model(request, obj, form, change)
        
        # Create a log entry for new payments or status changes
        if is_new:
            PaymentLog.objects.create(
                payment=obj,
                action="created_by_admin",
                performed_by=request.user,
                notes="Payment record created by admin"
            )
        elif original_status != obj.status:
            PaymentLog.objects.create(
                payment=obj,
                action=f"status_changed_to_{obj.status}",
                performed_by=request.user,
                notes=f"Status changed from {original_status} to {obj.status}"
            )
    
    def verify_payment(self, request, queryset):
        """Admin action to verify selected payments"""
        for payment in queryset:
            if not payment.confirmation_verified:
                payment.confirmation_verified = True
                payment.status = 'verified'
                payment.save()
                
                PaymentLog.objects.create(
                    payment=payment,
                    action="manually_verified",
                    performed_by=request.user,
                    notes="Payment manually verified by admin"
                )
        
        self.message_user(request, f"{queryset.count()} payment(s) marked as verified.")
    verify_payment.short_description = "Mark selected payments as verified"
    
    def approve_payment(self, request, queryset):
        """Admin action to approve selected payments"""
        for payment in queryset:
            if payment.status != 'approved':
                payment.status = 'approved'
                payment.save()
                
                PaymentLog.objects.create(
                    payment=payment,
                    action="approved",
                    performed_by=request.user,
                    notes="Payment approved by admin"
                )
        
        self.message_user(request, f"{queryset.count()} payment(s) approved.")
    approve_payment.short_description = "Approve selected payments"
    
    def reject_payment(self, request, queryset):
        """Admin action to reject selected payments"""
        for payment in queryset:
            if payment.status != 'rejected':
                payment.status = 'rejected'
                payment.save()
                
                PaymentLog.objects.create(
                    payment=payment,
                    action="rejected",
                    performed_by=request.user,
                    notes="Payment rejected by admin"
                )
        
        self.message_user(request, f"{queryset.count()} payment(s) rejected.")
    reject_payment.short_description = "Reject selected payments"
    
    actions = [verify_payment, approve_payment, reject_payment]


# Register the payment detail models separately
@admin.register(PayPalDetails)
class PayPalDetailsAdmin(admin.ModelAdmin):
    list_display = ('payment_reference', 'email', 'transaction_id')
    search_fields = ('email', 'transaction_id', 'payment__application__reference_number')
    
    def payment_reference(self, obj):
        """Return a link to the payment admin page"""
        if obj.payment:
            url = f"/admin/payment/payment/{obj.payment.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.payment)
        return "-"
    payment_reference.short_description = "Payment"
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion without deleting the parent payment
        return False


@admin.register(MpesaDetails)
class MpesaDetailsAdmin(admin.ModelAdmin):
    list_display = ('payment_reference', 'phone_number', 'mpesa_code', 'transaction_id')
    search_fields = ('phone_number', 'mpesa_code', 'transaction_id', 
                    'payment__application__reference_number')
    
    def payment_reference(self, obj):
        if obj.payment:
            url = f"/admin/payment/payment/{obj.payment.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.payment)
        return "-"
    payment_reference.short_description = "Payment"
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BankTransferDetails)
class BankTransferDetailsAdmin(admin.ModelAdmin):
    list_display = ('payment_reference', 'account_name', 'bank_name', 'reference_number')
    search_fields = ('account_name', 'bank_name', 'reference_number', 
                    'payment__application__reference_number')
    
    def payment_reference(self, obj):
        if obj.payment:
            url = f"/admin/payment/payment/{obj.payment.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.payment)
        return "-"
    payment_reference.short_description = "Payment"
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CardPaymentDetails)
class CardPaymentDetailsAdmin(admin.ModelAdmin):
    list_display = ('payment_reference', 'card_type', 'last_four', 'cardholder_name')
    search_fields = ('card_type', 'last_four', 'cardholder_name', 
                    'payment__application__reference_number')
    
    def payment_reference(self, obj):
        if obj.payment:
            url = f"/admin/payment/payment/{obj.payment.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.payment)
        return "-"
    payment_reference.short_description = "Payment"
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ('payment', 'action', 'performed_by', 'timestamp')
    list_filter = ('action', 'performed_by', 'timestamp')
    search_fields = ('payment__application__reference_number', 'notes')
    readonly_fields = ('payment', 'action', 'performed_by', 'notes', 'timestamp')
    
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
