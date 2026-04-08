from django.conf import settings
from django.db import models
from django.utils import timezone


class MembershipPlan(models.Model):
    name = models.CharField(max_length=100)
    duration_days = models.PositiveIntegerField(default=30, help_text="Abonemento galiojimo trukmė dienomis")
    visit_limit = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Apsilankymų limitas (jei nėra – neribotas)"
    )
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    def __str__(self):
        return self.name


class Membership(models.Model):
    STATUS_CHOICES = (
        ("ACTIVE", "Aktyvus"),
        ("EXPIRED", "Pasibaigęs"),
        ("PAUSED", "Sustabdyta"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT)

    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField()

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")
    visits_left = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} – {self.plan.name}"


class MembershipPurchase(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Laukiama apmokėjimo"),
        ("PAID", "Apmokėta"),
        ("REJECTED", "Atmesta"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")

    def __str__(self):
        return f"{self.user.username} – {self.plan.name} ({self.status})"


class Training(models.Model):
    title = models.CharField(max_length=100)
    starts_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)

    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="trainings"
    )

    description = models.TextField(blank=True)
    image_url = models.URLField(
        blank=True,
        help_text="Nuoroda į treniruotės paveikslą (URL)"
    )

    capacity = models.PositiveIntegerField(default=10)

    STATUS_CHOICES = (
        ("SCHEDULED", "Planuojama"),
        ("CANCELLED", "Atšaukta"),
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="SCHEDULED"
    )

    cancellation_note = models.CharField(
        max_length=255,
        blank=True
    )


    def __str__(self):
        return f"{self.title} ({self.starts_at:%Y-%m-%d %H:%M})"



class Reservation(models.Model):
    STATUS_CHOICES = (
        ("BOOKED", "Užregistruota"),
        ("CANCELLED", "Atšaukta"),
        ("ATTENDED", "Dalyvavo"),
        ("NO_SHOW", "Neatvyko"),
    )

    training = models.ForeignKey(
        Training,
        on_delete=models.CASCADE,
        related_name="reservations"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="BOOKED"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("training", "user")

    def __str__(self):
        return f"{self.user.username} → {self.training.title}"
