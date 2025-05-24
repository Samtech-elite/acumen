from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_application_email(user, status, reason=None, payment_url=None):
    if status == "approved":
        subject = "🎉 Congratulations! Your Application Has Been Approved"
        html_message = render_to_string("emails/approved.html", {
            'user': user,
            'payment_url': payment_url
        })
    elif status == "rejected":
        subject = "Update on Your Application to Acumen Ink"
        html_message = render_to_string("emails/rejected.html", {
            'user': user,
            'reason': reason
        })
    else:
        return

    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        "no-reply@acumenink.com",
        [user.email],
        html_message=html_message
    )

def send_application_confirmation_email(application):
    """Send confirmation email to user after submitting an application"""
    subject = "Application Received - Acumen Ink"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = application.applicant.user.email
    
    # Prepare context for email templates
    context = {
        'application': application,
    }
    
    # Render email templates
    text_content = render_to_string('emails/application_submitted.txt', context)
    html_content = render_to_string('emails/application_submitted.html', context)
    
    # Create email message with both text and HTML versions
    email = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    email.attach_alternative(html_content, "text/html")
    
    # Send the email
    return email.send()
