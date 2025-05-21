from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

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
