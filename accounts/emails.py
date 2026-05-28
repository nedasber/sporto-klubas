"""
Email pagalbinės funkcijos – siunčia laiškus per Resend API.
"""
import resend
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse

from .models import EmailLog

resend.api_key = settings.RESEND_API_KEY


def _send(subject, text_body, html_body, to_email):
    """Bendra siuntimo funkcija per Resend API."""
    params = {
        "from": settings.DEFAULT_FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }
    resend.Emails.send(params)


def send_verification_email(user, request=None):
    profile = user.profile
    token = profile.generate_new_token()

    verify_path = reverse("verify_email", args=[token])
    if request is not None:
        verify_url = request.build_absolute_uri(verify_path)
    else:
        verify_url = f"{settings.SITE_URL.rstrip('/')}{verify_path}"

    subject = "Patvirtinkite savo paskyrą – Sporto klubas"
    context = {"user": user, "verify_url": verify_url}

    _send(
        subject,
        render_to_string("accounts/emails/verify_email.txt", context),
        render_to_string("accounts/emails/verify_email.html", context),
        user.email,
    )
    return verify_url


def send_training_cancelled(reservation):
    user = reservation.user
    training = reservation.training

    if not user.email:
        return False

    already_sent = EmailLog.objects.filter(
        user=user, kind="training_cancelled", object_id=training.id
    ).exists()
    if already_sent:
        return False

    context = {
        "user": user,
        "training": training,
        "site_url": settings.SITE_URL.rstrip("/"),
    }

    try:
        _send(
            f"Treniruotė atšaukta: {training.title}",
            render_to_string("accounts/emails/training_cancelled.txt", context),
            render_to_string("accounts/emails/training_cancelled.html", context),
            user.email,
        )
        EmailLog.objects.create(user=user, kind="training_cancelled", object_id=training.id)
        return True
    except Exception as exc:
        print(f"[email error] training_cancelled to {user.email}: {exc}")
        return False


def send_training_reminder(reservation, reminder_type="day"):
    user = reservation.user
    training = reservation.training

    if not user.email:
        return False

    kind = "training_reminder_day" if reminder_type == "day" else "training_reminder_hour"

    if EmailLog.objects.filter(user=user, kind=kind, object_id=training.id).exists():
        return False

    context = {
        "user": user,
        "training": training,
        "reminder_type": reminder_type,
        "site_url": settings.SITE_URL.rstrip("/"),
    }

    subject_prefix = "Treniruotė už 1 val." if reminder_type == "hour" else "Rytdienos treniruotė"

    try:
        _send(
            f"{subject_prefix}: {training.title}",
            render_to_string("accounts/emails/training_reminder.txt", context),
            render_to_string("accounts/emails/training_reminder.html", context),
            user.email,
        )
        EmailLog.objects.create(user=user, kind=kind, object_id=training.id)
        return True
    except Exception as exc:
        print(f"[email error] training_reminder to {user.email}: {exc}")
        return False


def send_membership_expiring(membership, days_left):
    user = membership.user

    if not user.email:
        return False

    if EmailLog.objects.filter(
        user=user, kind="membership_expiring", object_id=membership.id
    ).exists():
        return False

    context = {
        "user": user,
        "membership": membership,
        "days_left": days_left,
        "site_url": settings.SITE_URL.rstrip("/"),
    }

    try:
        _send(
            f"Jūsų abonementas baigsis po {days_left} d.",
            render_to_string("accounts/emails/membership_expiring.txt", context),
            render_to_string("accounts/emails/membership_expiring.html", context),
            user.email,
        )
        EmailLog.objects.create(user=user, kind="membership_expiring", object_id=membership.id)
        return True
    except Exception as exc:
        print(f"[email error] membership_expiring to {user.email}: {exc}")
        return False


def send_membership_purchased(membership):
    user = membership.user

    if not user.email:
        return False

    if EmailLog.objects.filter(
        user=user, kind="membership_purchased", object_id=membership.id
    ).exists():
        return False

    context = {
        "user": user,
        "membership": membership,
        "site_url": settings.SITE_URL.rstrip("/"),
    }

    try:
        _send(
            "Apmokėjimas sėkmingas – Sporto klubas",
            render_to_string("accounts/emails/membership_purchased.txt", context),
            render_to_string("accounts/emails/membership_purchased.html", context),
            user.email,
        )
        EmailLog.objects.create(user=user, kind="membership_purchased", object_id=membership.id)
        return True
    except Exception as exc:
        print(f"[email error] membership_purchased to {user.email}: {exc}")
        return False