from django.apps import AppConfig


class GymConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gym"
    verbose_name = "Sporto klubas"

    def ready(self):
        from . import signals  # noqa: F401
