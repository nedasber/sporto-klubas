from django.conf import settings
from django.db import models
from django.utils import timezone

class MembershipPlan(models.Model):
    name = models.CharField(max_length=100, verbose_name="Pavadinimas")
    duration_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Galiojimo trukmė (dienomis)",
        help_text="Abonemento galiojimo trukmė dienomis"
    )
    visit_limit = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Apsilankymų limitas",
        help_text="Apsilankymų limitas (jei nėra – neribotas)"
    )
    price = models.DecimalField(
        max_digits=6, decimal_places=2, default=0.00,
        verbose_name="Kaina (€)"
    )

    class Meta:
        verbose_name = "Abonemento planas"
        verbose_name_plural = "Abonementų planai"

    def __str__(self):
        return self.name


class Membership(models.Model):
    STATUS_CHOICES = (
        ("ACTIVE", "Aktyvus"),
        ("EXPIRED", "Pasibaigęs"),
        ("PAUSED", "Sustabdyta"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name="Vartotojas"
    )
    plan = models.ForeignKey(
        MembershipPlan, on_delete=models.PROTECT,
        verbose_name="Planas"
    )

    start_date = models.DateField(default=timezone.now, verbose_name="Pradžios data")
    end_date = models.DateField(verbose_name="Pabaigos data")

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="ACTIVE",
        verbose_name="Būsena"
    )
    visits_left = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Liko apsilankymų"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Sukurta")

    class Meta:
        verbose_name = "Narystė"
        verbose_name_plural = "Narystės"

    def __str__(self):
        return f"{self.user.username} – {self.plan.name}"


class MembershipPurchase(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Laukiama apmokėjimo"),
        ("PAID", "Apmokėta"),
        ("REJECTED", "Atmesta"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name="Vartotojas"
    )
    plan = models.ForeignKey(
        MembershipPlan, on_delete=models.PROTECT,
        verbose_name="Planas"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Sukurta")

    full_name = models.CharField(max_length=120, verbose_name="Pilnas vardas")
    phone = models.CharField(max_length=30, blank=True, verbose_name="Telefonas")

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="PENDING",
        verbose_name="Būsena"
    )

    stripe_session_id = models.CharField(max_length=255, blank=True, verbose_name="Stripe sesijos ID")
    stripe_payment_intent = models.CharField(max_length=255, blank=True, verbose_name="Stripe mokėjimo ID")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Apmokėjimo data")

    class Meta:
        verbose_name = "Pirkimas"
        verbose_name_plural = "Pirkimai"

    def __str__(self):
        return f"{self.user.username} – {self.plan.name} ({self.status})"
class Training(models.Model):
    STATUS_CHOICES = (
        ("SCHEDULED", "Planuojama"),
        ("CANCELLED", "Atšaukta"),
    )

    title = models.CharField(max_length=100, verbose_name="Pavadinimas")
    starts_at = models.DateTimeField(verbose_name="Pradžia")
    duration_minutes = models.PositiveIntegerField(default=60, verbose_name="Trukmė (min)")

    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="trainings",
        verbose_name="Treneris"
    )

    description = models.TextField(blank=True, verbose_name="Aprašymas")

    image = models.ImageField(
        upload_to="trainings/",
        blank=True,
        null=True,
        verbose_name="Paveikslėlis",
        help_text="Įkeltas paveikslėlio failas (jpg, png)"
    )
    image_url = models.URLField(
        blank=True,
        verbose_name="Paveikslėlio nuoroda",
        help_text="Arba nuoroda į galerijos paveikslėlį"
    )

    capacity = models.PositiveIntegerField(default=10, verbose_name="Talpa (žmonių)")

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="SCHEDULED",
        verbose_name="Būsena"
    )

    cancellation_note = models.CharField(
        max_length=255, blank=True,
        verbose_name="Atšaukimo priežastis"
    )

    created_at = models.DateTimeField(default=timezone.now, verbose_name="Sukurta")

    class Meta:
        verbose_name = "Treniruotė"
        verbose_name_plural = "Treniruotės"

    def get_image_url(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return ""

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
        Training, on_delete=models.CASCADE, related_name="reservations",
        verbose_name="Treniruotė"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name="Vartotojas"
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="BOOKED",
        verbose_name="Būsena"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Sukurta")

    class Meta:
        unique_together = ("training", "user")
        verbose_name = "Rezervacija"
        verbose_name_plural = "Rezervacijos"

    def __str__(self):
        return f"{self.user.username} → {self.training.title}"
