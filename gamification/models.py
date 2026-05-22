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

    # Taškų ribos kiekvienam lygiui
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
    )
    points = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(choices=LEVEL_CHOICES, default=1)

    # Streak'ai
    current_streak = models.PositiveIntegerField(
        default=0,
        help_text="Dabartinis dienų iš eilės streak'as (paskutinė dalyvavimo data + sekančios dienos)"
    )
    longest_streak = models.PositiveIntegerField(
        default=0,
        help_text="Ilgiausias streak'as kada nors pasiektas"
    )
    last_attendance_date = models.DateField(
        null=True, blank=True,
        help_text="Paskutinė data, kai dalyvavo treniruotėje"
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} – {self.get_level_display()} ({self.points} t.)"

    def add_points(self, amount: int):
        """Prideda taškų ir, jei reikia, atnaujina lygį."""
        self.points += amount
        self.update_level()
        self.save()

    def update_level(self):
        """Atnaujina vartotojo lygį pagal sukauptus taškus."""
        new_level = 1
        for level, threshold in self.LEVEL_THRESHOLDS.items():
            if self.points >= threshold:
                new_level = level
        self.level = new_level

    def progress_to_next_level(self):
        """Grąžina procentą iki kito lygio (0–100)."""
        if self.level >= 5:
            return 100
        current_threshold = self.LEVEL_THRESHOLDS[self.level]
        next_threshold = self.LEVEL_THRESHOLDS[self.level + 1]
        progress = self.points - current_threshold
        total = next_threshold - current_threshold
        return int((progress / total) * 100) if total > 0 else 0

    def points_to_next_level(self):
        """Grąžina, kiek taškų trūksta iki kito lygio."""
        if self.level >= 5:
            return 0
        return self.LEVEL_THRESHOLDS[self.level + 1] - self.points

    def update_streak(self, attendance_date=None):
        """
        Atnaujina streak'ą po dalyvavimo treniruotėje.
        - Jei dalyvavo šiandien arba vakar po paskutinio karto – streak'as tęsiasi (+1)
        - Jei tarpas > 1 d. – streak'as resetinasi į 1
        - Jei dalyvavo tą pačią dieną du kartus – streak'as nesikeičia
        """
        if attendance_date is None:
            attendance_date = timezone.now().date()

        if self.last_attendance_date is None:
            # Pirmas dalyvavimas
            self.current_streak = 1
        elif attendance_date == self.last_attendance_date:
            # Tą pačią dieną – nieko nedarom
            return
        else:
            days_gap = (attendance_date - self.last_attendance_date).days
            if days_gap == 1:
                # Sekanti diena – streak'as tęsiasi
                self.current_streak += 1
            else:
                # Praleido dieną – streak'as nulinis ir prasideda nuo 1
                self.current_streak = 1

        # Atnaujinam ilgiausią
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

        self.last_attendance_date = attendance_date
        self.save(update_fields=["current_streak", "longest_streak", "last_attendance_date", "updated_at"])

    def is_active_member(self):
        """Aktyvus narys – dalyvavo bent kartą per pastarąsias 30 d."""
        if not self.last_attendance_date:
            return False
        days_since = (timezone.now().date() - self.last_attendance_date).days
        return days_since <= 30


class Achievement(models.Model):
    """Pasiekimas (ženklelis), kurį vartotojas gali gauti."""

    code = models.CharField(max_length=50, unique=True, help_text="Unikalus kodas, pvz. 'first_training'")
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    icon = models.CharField(max_length=50, default="trophy", help_text="Bootstrap Icon pavadinimas be 'bi-' priešdėlio")
    points_reward = models.PositiveIntegerField(default=50, help_text="Kiek taškų skiriama gavus pasiekimą")

    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    """Pasiekimo priskyrimas vartotojui."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "achievement")
        ordering = ["-earned_at"]

    def __str__(self):
        return f"{self.user.username} → {self.achievement.name}"
