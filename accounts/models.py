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
        ("CLIENT", "Klientas"),
        ("TRAINER", "Treneris"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile",
        verbose_name="Vartotojas"
    )
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="CLIENT",
        verbose_name="Rolė"
    )

    last_notifications_seen_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Paskutinė pranešimų peržiūra"
    )

    # ----- EMAIL VERIFIKACIJA -----
    email_verified = models.BooleanField(
        default=False,
        verbose_name="El. paštas patvirtintas"
    )
    verification_token = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Patvirtinimo žetonas"
    )
    verification_sent_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Žetonas išsiųstas"
    )

    class Meta:
        verbose_name = "Profilis"
        verbose_name_plural = "Profiliai"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    def generate_new_token(self):
        self.verification_token = _generate_token()
        self.verification_sent_at = timezone.now()
        self.save(update_fields=["verification_token", "verification_sent_at"])
        return self.verification_token


class EmailLog(models.Model):
    """Apsauga nuo dvigubo siuntimo."""
    KIND_CHOICES = (
        ("training_cancelled", "Treniruotė atšaukta"),
        ("training_reminder_day", "Priminimas dieną prieš"),
        ("training_reminder_hour", "Priminimas 1 val. prieš"),
        ("membership_expiring", "Abonementas baigiasi"),
        ("membership_purchased", "Abonementas nupirktas"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_logs",
        verbose_name="Vartotojas"
    )
    kind = models.CharField(max_length=50, choices=KIND_CHOICES, verbose_name="Tipas")
    object_id = models.PositiveIntegerField(verbose_name="Objekto ID")
    sent_at = models.DateTimeField(default=timezone.now, verbose_name="Išsiųsta")

    class Meta:
        unique_together = ("user", "kind", "object_id")
        ordering = ["-sent_at"]
        verbose_name = "El. laiško žurnalas"
        verbose_name_plural = "El. laiškų žurnalas"

    def __str__(self):
        return f"{self.user.username} - {self.kind} #{self.object_id}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance, defaults={"role": "CLIENT"})
