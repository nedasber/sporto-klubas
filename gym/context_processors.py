"""
Kontekstų procesoriai – pridedami į kiekvieno puslapio kontekstą.
"""
from django.utils import timezone


def notifications(request):
    """
    Suskaičiuoja naujų treniruočių sk. ir grąžina jų sąrašą.
    „Nauja" = treniruotė sukurta po vartotojo paskutinio pranešimų peržiūrėjimo.
    Veikia tik prisijungusiems klientams.
    """
    if not request.user.is_authenticated:
        return {}

    try:
        profile = request.user.profile
    except Exception:
        return {}

    # Tik klientams
    if profile.role != "CLIENT":
        return {
            "notifications_count": 0,
            "notifications_list": [],
        }

    from gym.models import Training

    since = profile.last_notifications_seen_at
    now = timezone.now()

    # Naujos treniruotės: sukurtos po paskutinio peržiūrėjimo, dar nepraėjusios, ne atšauktos
    new_trainings = Training.objects.filter(
        created_at__gt=since,
        starts_at__gte=now,
        status="SCHEDULED",
    ).select_related("trainer").order_by("-created_at")

    return {
        "notifications_count": new_trainings.count(),
        "notifications_list": list(new_trainings[:10]),
    }
