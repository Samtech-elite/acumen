from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, ApplicantProfileForm, ApplicationForm
from .models import ApplicantProfile, Application
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render, redirect
from .utils import send_application_email
from django.utils.timezone import now

@login_required
def submit_application(request):
    applicant_profile = get_object_or_404(ApplicantProfile, user=request.user)

    # Check if user already has a pending or approved application
    existing = Application.objects.filter(applicant=applicant_profile).exclude(status='rejected').first()
    if existing:
        messages.info(request, "You already have an active application.")
        return redirect('application_status')

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = applicant_profile
            application.save()
            messages.success(request, "Application submitted successfully!")
            return redirect('thank_you')
    else:
        form = ApplicationForm()

    return render(request, 'applications/application_form.html', {'form': form})

@login_required
def application_status(request):
    applicant_profile = get_object_or_404(ApplicantProfile, user=request.user)
    application = Application.objects.filter(applicant=applicant_profile).order_by('-submitted_at').first()

    return render(request, 'applications/application_status.html', {
        'application': application,
    })

def thank_you(request):
    # After submission page with referral/share prompt
    return render(request, 'applications/thank_you.html')


@staff_member_required
def preview_email(request, pk):
    app = get_object_or_404(Application, pk=pk)
    if app.status == "approved":
        return render(request, "emails/approved.html", {
            'user': app.applicant.user,
            'payment_url': "https://acumenink.com/payment"
        })
    elif app.status == "rejected":
        return render(request, "emails/rejected.html", {
            'user': app.applicant.user,
            'reason': app.rejection_reason
        })

@staff_member_required
def resend_email_view(request, pk):
    app = get_object_or_404(Application, pk=pk)
    try:
        send_application_email(
            user=app.applicant.user,
            status=app.status,
            reason=app.rejection_reason,
            payment_url="https://acumenink.com/payment"
        )
        app.email_status = "sent"
        app.email_last_sent_at = now()
    except Exception:
        app.email_status = "failed"
    app.save()
    return redirect('/admin/applications/application/')

@login_required
def application_details(request, pk):
    """
    Display detailed information about a specific application.
    Regular users can only view their own applications.
    Staff members can view any application.
    """
    application = get_object_or_404(Application, pk=pk)
    
    # Security check: ensure users can only see their own applications
    if not request.user.is_staff and application.applicant.user != request.user:
        messages.error(request, "You do not have permission to view this application.")
        return redirect('application_status')
        
    # Check if there's an update message in the session
    message = None
    if 'status_update' in request.session:
        message = request.session['status_update']
        del request.session['status_update']
        
    return render(request, 'applications/application_details.html', {
        'application': application,
        'message': message,
        'can_edit': application.status == 'pending' and application.applicant.user == request.user,
    })

@login_required
def edit_application(request, pk):
    """
    Allows users to edit their pending applications.
    Only the original applicant can edit, and only if status is 'pending'.
    """
    application = get_object_or_404(Application, pk=pk)
    
    # Security check: ensure users can only edit their own pending applications
    if application.applicant.user != request.user:
        messages.error(request, "You do not have permission to edit this application.")
        return redirect('application_status')
    
    # Can only edit pending applications
    if application.status != 'pending':
        messages.error(request, "You can only edit pending applications.")
        return redirect('application_details', pk=application.pk)
    
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES, instance=application)
        if form.is_valid():
            application = form.save(commit=False)
            application.last_updated = now()  # Update timestamp
            application.save()
            messages.success(request, "Application updated successfully!")
            return redirect('application_details', pk=application.pk)
    else:
        form = ApplicationForm(instance=application)
    
    return render(request, 'applications/edit_application.html', {
        'form': form,
        'application': application
    })
