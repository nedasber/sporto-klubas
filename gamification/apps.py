from django.apps import AppConfig


class GamificationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gamification"
    verbose_name = "Motyvacinė sistema"

    # SVARBU: ready() metodas paleidziamas, kai Django uzkrauna sia app'a.
    # Cia importuojam signals modulį, kad signal'ai butu registruoti ir veiktu.
    # BE SITO signal'ai NEPALEIDZIA - tasku/pasiekimu sistema neveiks.
    def ready(self):
        from . import signals
