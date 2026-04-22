from django.conf import settings
from django.db import models
from django.utils import timezone


class UserProgress(models.Model):
    """Saugo vartotojo bendrą pažangą – taškus ir dabartinį lygį."""

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
