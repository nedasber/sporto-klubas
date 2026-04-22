from django.apps import AppConfig


class GamificationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gamification"
    verbose_name = "Motyvacinė sistema"

    def ready(self):
        # Importuojame signalus, kad jie būtų užregistruoti
        from . import signals  # noqa: F401
