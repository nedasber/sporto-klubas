from django.conf import settings
from django.db import models
from django.utils import timezone


class UserProgress(models.Model):
    """Saugo vartotojo bendrą pažangą – taškus, lygį ir streak'us."""

    LEVEL_CHOICES = (
        (1, "Pradedantysis"),
        (2, "Sportininkas"),
        (3, "Atletas"),
        (4, "Čempionas"),
        (5, "Legenda"),
    )

    LEVEL_THRESHOLDS = {
        1: 0,
        2: 100,
        3: 300,
        4: 700,
        5: 1500,
    }

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="progress",
        verbose_name="Vartotojas"
    )
    points = models.PositiveIntegerField(default=0, verbose_name="Taškai")
    level = models.PositiveIntegerField(choices=LEVEL_CHOICES, default=1, verbose_name="Lygis")

    current_streak = models.PositiveIntegerField(
        default=0,
        verbose_name="Dabartinis streak'as",
        help_text="Dabartinis dienų iš eilės skaičius"
    )
    longest_streak = models.PositiveIntegerField(
        default=0,
        verbose_name="Ilgiausias streak'as"
    )
    last_attendance_date = models.DateField(
        null=True, blank=True,
        verbose_name="Paskutinis dalyvavimas"
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atnaujinta")

    class Meta:
        verbose_name = "Vartotojo pažanga"
        verbose_name_plural = "Vartotojų pažanga"

    def __str__(self):
        return f"{self.user.username} – {self.get_level_display()} ({self.points} t.)"

    def add_points(self, amount: int):
        self.points += amount
        self.update_level()
        self.save()

    def update_level(self):
        new_level = 1
        for level, threshold in self.LEVEL_THRESHOLDS.items():
            if self.points >= threshold:
                new_level = level
        self.level = new_level

    def progress_to_next_level(self):
        if self.level >= 5:
            return 100
        current_threshold = self.LEVEL_THRESHOLDS[self.level]
        next_threshold = self.LEVEL_THRESHOLDS[self.level + 1]
        progress = self.points - current_threshold
        total = next_threshold - current_threshold
        return int((progress / total) * 100) if total > 0 else 0

    def points_to_next_level(self):
        if self.level >= 5:
            return 0
        return self.LEVEL_THRESHOLDS[self.level + 1] - self.points

    def update_streak(self, attendance_date=None):
        if attendance_date is None:
            attendance_date = timezone.now().date()

        if self.last_attendance_date is None:
            self.current_streak = 1
        elif attendance_date == self.last_attendance_date:
            return
        else:
            days_gap = (attendance_date - self.last_attendance_date).days
            if days_gap == 1:
                self.current_streak += 1
            else:
                self.current_streak = 1

        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

        self.last_attendance_date = attendance_date
        self.save(update_fields=["current_streak", "longest_streak", "last_attendance_date", "updated_at"])

    def is_active_member(self):
        if not self.last_attendance_date:
            return False
        days_since = (timezone.now().date() - self.last_attendance_date).days
        return days_since <= 30


class Achievement(models.Model):
    """Pasiekimas (ženklelis), kurį vartotojas gali gauti."""

    code = models.CharField(
        max_length=50, unique=True,
        verbose_name="Kodas",
        help_text="Unikalus kodas, pvz. 'first_training'"
    )
    name = models.CharField(max_length=100, verbose_name="Pavadinimas")
    description = models.CharField(max_length=255, verbose_name="Aprašymas")
    icon = models.CharField(
        max_length=50, default="trophy",
        verbose_name="Piktograma",
        help_text="Bootstrap Icon pavadinimas be 'bi-' priešdėlio"
    )
    points_reward = models.PositiveIntegerField(
        default=50,
        verbose_name="Taškų atlygis",
        help_text="Kiek taškų skiriama gavus pasiekimą"
    )

    class Meta:
        verbose_name = "Pasiekimas"
        verbose_name_plural = "Pasiekimai"

    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    """Pasiekimo priskyrimas vartotojui."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="achievements",
        verbose_name="Vartotojas"
    )
    achievement = models.ForeignKey(
        Achievement, on_delete=models.CASCADE,
        verbose_name="Pasiekimas"
    )
    earned_at = models.DateTimeField(default=timezone.now, verbose_name="Gauta")

    class Meta:
        unique_together = ("user", "achievement")
        ordering = ["-earned_at"]
        verbose_name = "Gautas pasiekimas"
        verbose_name_plural = "Gauti pasiekimai"

    def __str__(self):
        return f"{self.user.username} → {self.achievement.name}"
