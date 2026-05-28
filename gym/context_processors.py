"""
Kontekstų procesoriai – pridedami į kiekvieno puslapio kontekstą.
"""
from django.utils import timezone


def notifications(request):
    """
    Pranesimai varpelyje klientui:
    1. Naujos treniruotes (sukurtos po paskutinio perziurejimo)
    2. Atsauktos treniruotes (atsauktos po paskutinio perziurejimo)

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
            "notifications_new_trainings": [],
            "notifications_cancelled_trainings": [],
        }

    from gym.models import Training, Reservation

    # SVARBU: jei naujas vartotojas, last_notifications_seen_at gali būti None.
    # Tokiu atveju naudojam user.date_joined kaip atskaitos tašką
    since = profile.last_notifications_seen_at or request.user.date_joined
    now = timezone.now()

    # 1. NAUJOS treniruotes - sukurtos po paskutinio perziurejimo
    new_trainings = list(
        Training.objects.filter(
            created_at__gt=since,
            starts_at__gte=now,
            status="SCHEDULED",
        ).select_related("trainer").order_by("-created_at")[:10]
    )

    # 2. ATSAUKTOS treniruotes - atsauktos PO paskutinio perziurejimo.
    # Klientas turi buti uzsiregistraves (BOOKED rezervacija) IR treniruote dar nepraejusi.
    cancelled_reservations = list(
        Reservation.objects.filter(
            user=request.user,
            status="BOOKED",  # klientas buvo uzsiregistraves
            training__status="CANCELLED",  # bet treniruote atsaukta
            training__cancelled_at__gt=since,  # atsaukta po paskutinio perziurejimo
            training__starts_at__gte=now,  # tik busimos
        ).select_related("training", "training__trainer")
        .order_by("-training__cancelled_at")[:10]
    )

    cancelled_trainings = [r.training for r in cancelled_reservations]

    total_count = len(new_trainings) + len(cancelled_trainings)

    return {
        "notifications_count": total_count,
        "notifications_new_trainings": new_trainings,
        "notifications_cancelled_trainings": cancelled_trainings,
        # Backward compatibility - jei kazkur naudojama notifications_list
        "notifications_list": new_trainings,
    }
