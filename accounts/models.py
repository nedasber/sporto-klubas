import secrets
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


def _generate_token():
    return secrets.token_urlsafe(48)


class Profile(models.Model):
    ROLE_CHOICES = (
        ("CLIENT", "Client"),
        ("TRAINER", "Trainer"),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="CLIENT")

    last_notifications_seen_at = models.DateTimeField(default=timezone.now)

    # Email verifikacija
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=128, blank=True)
    verification_sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def generate_new_token(self):
        self.verification_token = _generate_token()
        self.verification_sent_at = timezone.now()
        self.save(update_fields=["verification_token", "verification_sent_at"])
        return self.verification_token


class EmailLog(models.Model):
    """
    Apsauga nuo dvigubo siuntimo.
    Saugom įrašą kiekvieną kartą, kai išsiųstas tam tikro tipo laiškas
    konkrečiam vartotojui apie konkretų objektą (treniruotę / abonementą).
    """
    KIND_CHOICES = (
        ("training_cancelled", "Training cancelled"),
        ("training_reminder_day", "Training reminder - 1 day before"),
        ("training_reminder_hour", "Training reminder - 1 hour before"),
        ("membership_expiring", "Membership expiring soon"),
        ("membership_purchased", "Membership purchased"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_logs")
    kind = models.CharField(max_length=50, choices=KIND_CHOICES)
    object_id = models.PositiveIntegerField(
        help_text="ID susijusio objekto (training_id arba membership_id), kad nesiųsti dukart"
    )
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "kind", "object_id")
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.user.username} - {self.kind} #{self.object_id}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance, defaults={"role": "CLIENT"})
