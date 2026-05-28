from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import secrets


# Token generavimas - kryptografiškai stiprus (ne random)
def _generate_token():
    return secrets.token_urlsafe(48)


# Vartotojo profilis - papildomi laukai prie Django User
class Profile(models.Model):

    # SVARBU: pridėjau ADMIN rolę.
    # Django turi is_superuser/is_staff, bet Profile.role naudoju verslo logikai
    ROLE_CHOICES = (
        ("CLIENT", "Klientas"),
        ("TRAINER", "Treneris"),
        ("ADMIN", "Administratorius"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Vartotojas"
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default="CLIENT",
        verbose_name="Rolė"
    )

    # Email patvirtinimo laukai
    email_verified = models.BooleanField(default=False, verbose_name="El. paštas patvirtintas")
    verification_token = models.CharField(max_length=100, blank=True, default="", verbose_name="Patvirtinimo token")
    verification_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Token sukurtas")

    # Pranešimų varpelio "read state" - vietoj atskiros Notification lentelės
    last_notifications_seen_at = models.DateTimeField(null=True, blank=True, verbose_name="Paskutinį kartą peržiūrėjo pranešimus")

    class Meta:
        verbose_name = "Profilis"
        verbose_name_plural = "Profiliai"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    # Generuoja naują token email patvirtinimui
    def generate_new_token(self):
        self.verification_token = _generate_token()
        self.verification_sent_at = timezone.now()
        self.save(update_fields=["verification_token", "verification_sent_at"])
        return self.verification_token


# Email log - audit log su idempotency apsauga
class EmailLog(models.Model):
    KIND_CHOICES = (
        ("verification", "Email patvirtinimas"),
        ("training_cancelled", "Treniruotė atšaukta"),
        ("reminder_day", "Priminimas (24h)"),
        ("reminder_hour", "Priminimas (1h)"),
        ("membership_expiring", "Abonementas baigsis"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField(max_length=30, choices=KIND_CHOICES)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # SVARBU: unique_together užtikrina, kad tas pats email nebūtų išsiųstas du kartus.
        # Tai DB lygmens apsauga - jei cron'as paleidžiamas dukart, IntegrityError sustabdys dublikatą
        unique_together = ("user", "kind", "object_id")
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.user.username} - {self.get_kind_display()} ({self.sent_at})"


# Signal'as - automatiškai sukuria Profile, kai sukuriamas User.
# SVARBU: jei User yra superuser arba staff, priskiriam ADMIN rolę
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        # Default rolė - CLIENT, bet jei superuser/staff - ADMIN
        if instance.is_superuser or instance.is_staff:
            role = "ADMIN"
        else:
            role = "CLIENT"

        Profile.objects.get_or_create(
            user=instance,
            defaults={"role": role}
        )
    else:
        # Jei User jau egzistuoja ir tapo superuser/staff, atnaujinam jo profilį.
        # Tai apsauga, jei adminas keičiamas per Django shell ar admin'ę
        if hasattr(instance, "profile"):
            if (instance.is_superuser or instance.is_staff) and instance.profile.role != "ADMIN":
                instance.profile.role = "ADMIN"
                instance.profile.save(update_fields=["role"])
