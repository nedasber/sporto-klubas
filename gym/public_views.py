"""
Viešasis pradinis puslapis (landing page).
Matomas visiems, įskaitant neprisijungusius vartotojus.
"""
from django.shortcuts import render, redirect
from django.utils import timezone
from gym.models import Training, MembershipPlan


def home_page(request):
    """
    Pagrindinis viešas puslapis.
    - Prisijungę vartotojai nukreipiami į dashboard'ą
    - Neprisijungę mato viešą informacinį puslapį
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    now = timezone.now()

    # Artimiausios 6 treniruotės (būsimos, neatšauktos)
    upcoming_trainings = Training.objects.filter(
        starts_at__gte=now,
        status="SCHEDULED",
    ).select_related("trainer").order_by("starts_at")[:6]

    # Visi abonementų planai pagal kainą
    plans = MembershipPlan.objects.order_by("price")

    context = {
        "upcoming_trainings": upcoming_trainings,
        "plans": plans,
    }
    return render(request, "gym/home.html", context)
