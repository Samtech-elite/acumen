from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.timezone import now
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.db.models import Count, Avg, Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django import forms

from .models import Application, ApplicationLog
from .utils import send_application_email
from .forms import RejectionReasonForm


class ApplicationLogInline(admin.TabularInline):
    model = ApplicationLog
    extra = 0
    readonly_fields = ['action', 'admin', 'notes', 'timestamp']
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'applicant', 
        'status', 
        'submitted_at', 
        'email_status', 
        'email_last_sent_at', 
        'view_email_preview', 
        'resend_email_link'
    )
    list_filter = ('status', 'email_status', 'submitted_at')
    search_fields = ('applicant__user__email', 'applicant__user__username', 'applicant__country', 'status', 'email_status')
    ordering = ('-submitted_at',)
    readonly_fields = ('submitted_at', 'email_last_sent_at')
    actions = ['approve_applications', 'reject_applications_with_reason', 'resend_emails', 'mark_as_pending']
    change_list_template = "admin/applications_change_list.html"
    fieldsets = (
        ('Applicant Information', {
            'fields': ('applicant',)
        }),
        ('Application Details', {
            'fields': ('resume', 'writing_sample', 'cover_letter')
        }),
        ('Status Information', {
            'fields': ('status', 'rejection_reason')
        }),
        ('Email Information', {
            'fields': ('email_status', 'email_last_sent_at')
        }),
        ('Marketing Information', {
            'fields': ('heard_about', 'previous_application')
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('submitted_at',)
        }),
    )

    inlines = [ApplicationLogInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('stats/', self.admin_site.admin_view(self.application_stats_view), name='application_stats'),
            path('<int:application_id>/preview-email/', self.admin_site.admin_view(self.preview_email_view), name='preview_email'),
            path('<int:application_id>/resend-email/', self.admin_site.admin_view(self.resend_email_view), name='resend_email'),
            path('reject-with-reason/', self.admin_site.admin_view(self.reject_with_reason_view), name='reject_with_reason'),
        ]
        return custom_urls + urls

    def application_stats_view(self, request):
        status_counts = Application.objects.values('status').annotate(count=Count('id'))
        country_counts = (
            Application.objects.values('applicant__country')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        
        # Monthly application trend
        monthly_applications = (
            Application.objects
            .extra(select={'month': "EXTRACT(month FROM submitted_at)"})
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        
        # Weekly application trend
        weekly_applications = (
            Application.objects
            .extra(select={'week': "EXTRACT(week FROM submitted_at)"})
            .values('week')
            .annotate(count=Count('id'))
            .order_by('week')
        )
        
        # Marketing source stats
        source_stats = (
            Application.objects
            .values('heard_about')
            .exclude(heard_about__isnull=True)
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        context = dict(
            self.admin_site.each_context(request),
            status_counts=status_counts,
            country_counts=country_counts,
            monthly_applications=monthly_applications,
            weekly_applications=weekly_applications,
            source_stats=source_stats,
            title="Application Statistics",
        )
        return render(request, "admin/application_stats.html", context)

    def preview_email_view(self, request, application_id):
        """Preview the email that would be sent to the applicant"""
        try:
            app = Application.objects.get(pk=application_id)
            email_html = render_to_string(
                'emails/application_status.html',
                {
                    'user': app.applicant.user,
                    'status': app.status,
                    'reason': app.rejection_reason,
                    'payment_url': "https://acumenink.com/payment"
                }
            )
            return HttpResponse(email_html)
        except Application.DoesNotExist:
            messages.error(request, "Application not found")
            return redirect('admin:applications_application_changelist')

    def resend_email_view(self, request, application_id):
        """Resend the email for a specific application"""
        try:
            app = Application.objects.get(pk=application_id)
            if app.status in ['approved', 'rejected']:
                try:
                    send_application_email(
                        user=app.applicant.user,
                        status=app.status,
                        reason=app.rejection_reason,
                        payment_url="https://acumenink.com/payment"
                    )
                    app.email_status = 'sent'
                    app.email_last_sent_at = now()
                    app.save()
                    
                    # Log the action
                    ApplicationLog.objects.create(
                        application=app,
                        action='email_resent',
                        admin=request.user,
                        notes=f"Email resent by {request.user.username}"
                    )
                    
                    messages.success(request, f"Email resent to {app.applicant.user.email}")
                except Exception as e:
                    messages.error(request, f"Failed to resend email: {str(e)}")
            else:
                messages.warning(request, f"Cannot send email: application status is '{app.status}'")
        except Application.DoesNotExist:
            messages.error(request, "Application not found")
            
        return redirect('admin:applications_application_changelist')

    def reject_with_reason_view(self, request):
        """View for rejecting applications with a specific reason"""
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        
        if request.method == 'POST' and 'confirm' in request.POST:
            reason = request.POST.get('rejection_reason', '')
            return self._process_rejections(request, selected, reason)
        
        apps = Application.objects.filter(id__in=selected)
        form = RejectionReasonForm()
        
        context = dict(
            self.admin_site.each_context(request),
            title="Reject Applications with Reason",
            apps=apps,
            form=form,
            action_checkbox_name=admin.ACTION_CHECKBOX_NAME,
        )
        return render(request, 'admin/reject_with_reason.html', context)

    def _process_rejections(self, request, selected_ids, reason):
        """Process the actual rejection with the provided reason"""
        count = 0
        for app_id in selected_ids:
            try:
                app = Application.objects.get(pk=app_id)
                app.status = 'rejected'
                app.rejection_reason = reason
                app.save()
                
                # Log the action
                ApplicationLog.objects.create(
                    application=app,
                    action='rejected',
                    admin=request.user,
                    notes=f"Rejected with reason: {reason}"
                )
                
                try:
                    send_application_email(
                        user=app.applicant.user,
                        status='rejected',
                        reason=reason,
                        payment_url="https://acumenink.com/payment"
                    )
                    app.email_status = 'sent'
                    app.email_last_sent_at = now()
                    app.save()
                except Exception as e:
                    messages.error(request, f"Failed to send email to {app.applicant.user.email}: {str(e)}")
                count += 1
            except Application.DoesNotExist:
                continue
                
        messages.success(request, f"{count} application(s) rejected with the provided reason.")
        return redirect('admin:applications_application_changelist')

    def view_email_preview(self, obj):
        """Button to preview the email that would be sent"""
        url = reverse('admin:preview_email', args=[obj.pk])
        return format_html('<a href="{}" target="_blank" class="button">Preview</a>', url)
    view_email_preview.short_description = "Email Preview"

    def resend_email_link(self, obj):
        """Button to resend the email"""
        url = reverse('admin:resend_email', args=[obj.pk])
        return format_html('<a class="button" href="{}">Resend</a>', url)
    resend_email_link.short_description = "Resend Email"

    def resend_emails(self, request, queryset):
        """Action to resend emails for multiple applications"""
        count = 0
        for app in queryset:
            if app.status in ['approved', 'rejected']:
                try:
                    send_application_email(
                        user=app.applicant.user,
                        status=app.status,
                        reason=app.rejection_reason,
                        payment_url="https://acumenink.com/payment"
                    )
                    app.email_status = 'sent'
                    app.email_last_sent_at = now()
                    app.save()
                    
                    # Log the action
                    ApplicationLog.objects.create(
                        application=app,
                        action='email_resent',
                        admin=request.user,
                        notes=f"Email resent via bulk action"
                    )
                    
                    count += 1
                except Exception as e:
                    messages.error(request, f"Failed to resend email to {app.applicant.user.email}: {str(e)}")
            else:
                messages.warning(request, f"Skipping {app.applicant.user.email}: status is '{app.status}'")
        
        messages.success(request, f"Successfully resent {count} email(s)")
    resend_emails.short_description = "Resend approval/rejection emails"

    def approve_applications(self, request, queryset):
        """Action to approve multiple applications"""
        updated = 0
        for app in queryset:
            if app.status != 'approved':
                app.status = 'approved'
                app.rejection_reason = ''
                app.save()
                
                # Log the action
                ApplicationLog.objects.create(
                    application=app,
                    action='approved',
                    admin=request.user,
                    notes=f"Approved by {request.user.username}"
                )
                
                try:
                    send_application_email(
                        user=app.applicant.user,
                        status='approved',
                        reason='',
                        payment_url="https://acumenink.com/payment"
                    )
                    app.email_status = 'sent'
                    app.email_last_sent_at = now()
                    app.save()
                    updated += 1
                except Exception as e:
                    messages.error(request, f"Failed to send email to {app.applicant.user.email}: {str(e)}")
            else:
                messages.info(request, f"Application for {app.applicant.user.email} already approved.")
        
        messages.success(request, f"{updated} application(s) approved successfully.")
    approve_applications.short_description = "Approve selected applications"

    def mark_as_pending(self, request, queryset):
        """Mark applications as pending for review"""
        updated = queryset.update(status='pending', rejection_reason='')
        
        # Log the action for each application
        for app in queryset:
            ApplicationLog.objects.create(
                application=app,
                action='marked_pending',
                admin=request.user,
                notes=f"Marked as pending by {request.user.username}"
            )
        
        messages.success(request, f"{updated} application(s) marked as pending for review.")
    mark_as_pending.short_description = "Mark selected applications as pending"

    def reject_applications_with_reason(self, request, queryset):
        """Redirect to the custom view for rejecting with reason"""
        return redirect('admin:reject_with_reason')
    reject_applications_with_reason.short_description = "Reject selected applications (with reason)"

    def save_model(self, request, obj, form, change):
        """Override save_model to handle status changes and emails"""
        old_status = None
        if change:
            try:
                old_instance = self.model.objects.get(pk=obj.pk)
                old_status = old_instance.status
            except self.model.DoesNotExist:
                pass
        
        super().save_model(request, obj, form, change)
        
        # Log the action
        action_type = 'created' if not change else 'updated'
        if old_status and old_status != obj.status:
            action_type = f'status_changed_to_{obj.status}'
            
        ApplicationLog.objects.create(
            application=obj,
            action=action_type,
            admin=request.user,
            notes=f"Application {action_type} by {request.user.username}"
        )
        
        # Send email if status changed to approved or rejected
        if old_status and old_status != obj.status and obj.status in ['approved', 'rejected']:
            try:
                send_application_email(
                    user=obj.applicant.user,
                    status=obj.status,
                    reason=obj.rejection_reason,
                    payment_url="https://acumenink.com/payment"
                )
                obj.email_status = 'sent'
                obj.email_last_sent_at = now()
                obj.save()
                messages.success(request, f"Status updated and email sent to {obj.applicant.user.email}")
            except Exception as e:
                messages.error(request, f"Status updated but failed to send email: {str(e)}")


@admin.register(ApplicationLog)
class ApplicationLogAdmin(admin.ModelAdmin):
    list_display = ['application', 'action', 'admin', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['application__applicant__user__email', 'notes']
    readonly_fields = ['timestamp']
