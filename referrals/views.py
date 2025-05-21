from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import ReferralCode, Referral
from .forms import ReferralInviteForm
from django.contrib.auth.models import User


@login_required
def referral_dashboard(request):
    """
    Show the logged-in user's referral dashboard with stats and referral list.
    """
    referrals = Referral.objects.filter(referrer=request.user)
    referral_code_obj, created = ReferralCode.objects.get_or_create(user=request.user)

    total_referrals = referrals.count()
    total_applied = referrals.filter(status__in=['applied', 'approved', 'rejected']).count()
    total_approved = referrals.filter(status='approved').count()

    context = {
        'referrals': referrals,
        'referral_code': referral_code_obj,
        'total_referrals': total_referrals,
        'total_applied': total_applied,
        'total_approved': total_approved,
    }
    return render(request, 'referrals/dashboard.html', context)

@login_required
def invite_friend(request):
    """
    Allow logged-in users to invite friends by entering their email.
    Sends an invitation email with referral link.
    """
    if request.method == 'POST':
        form = ReferralInviteForm(request.POST, referrer=request.user)
        if form.is_valid():
            friend_email = form.cleaned_data['referred_email']
            referrer = request.user

            referral, created = Referral.objects.get_or_create(
                referrer=referrer,
                referred_email=friend_email,
                defaults={'status': 'invited'}
            )
            if not created:
                messages.info(request, f"You have already invited {friend_email}.")
                return redirect('referral_dashboard')

            referral_code_obj, _ = ReferralCode.objects.get_or_create(user=referrer)
            referral_link = referral_code_obj.get_referral_link()

            send_mail(
                subject="Join Acumen Ink as a Writer!",
                message=(
                    f"Hi! Your friend {referrer.get_full_name() or referrer.username} "
                    f"invited you to apply as a writer on Acumen Ink.\n\n"
                    f"Apply here: {referral_link}\n\n"
                    "We look forward to seeing your application!"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[friend_email],
                fail_silently=False,
            )

            messages.success(request, f"Invitation sent to {friend_email}!")
            return redirect('referral_dashboard')
    else:
        form = ReferralInviteForm(referrer=request.user)

    return render(request, 'referrals/invite.html', {'form': form})


@login_required
def invite_friend(request):
    if request.method == 'POST':
        form = ReferralInviteForm(request.POST, referrer=request.user)
        if form.is_valid():
            friend_email = form.cleaned_data['referred_email']
            referrer = request.user

            referral, created = Referral.objects.get_or_create(
                referrer=referrer,
                referred_email=friend_email,
                defaults={'status': 'invited'}
            )
            if not created:
                messages.info(request, f"You have already invited {friend_email}.")
                return redirect('referral_dashboard')

            referral_code_obj, _ = ReferralCode.objects.get_or_create(user=referrer)
            referral_link = referral_code_obj.get_referral_link()

            context = {
                'referrer_name': referrer.get_full_name() or referrer.username,
                'referral_link': referral_link,
            }

            subject = "Join Acumen Ink as a Writer!"
            from_email = settings.DEFAULT_FROM_EMAIL
            to = [friend_email]

            text_content = render_to_string('referrals/referral_invite_email.txt', context)
            html_content = render_to_string('referrals/referral_invite_email.html', context)

            msg = EmailMultiAlternatives(subject, text_content, from_email, to)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            messages.success(request, f"Invitation sent to {friend_email}!")
            return redirect('referral_dashboard')
    else:
        form = ReferralInviteForm(referrer=request.user)

    return render(request, 'referrals/invite.html', {'form': form})

