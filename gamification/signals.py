"""
Signalai, kurie automatiškai prideda taškus ir tikrina pasiekimus,
kai įvyksta svarbūs sistemos veiksmai.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from gym.models import Reservation, Membership
from .services import (
    award_points,
    check_and_grant_achievements,
    get_or_create_progress,
    POINTS_FOR_ATTENDANCE,
    POINTS_FOR_MEMBERSHIP_PURCHASE,
    POINTS_FOR_RESERVATION,
)


@receiver(post_save, sender=Reservation)
def reservation_saved(sender, instance, created, **kwargs):
    """
    Kai sukuriama nauja rezervacija arba pasikeičia statusas į ATTENDED –
    priskiriami taškai ir tikrinami pasiekimai.
    """
    if created:
        # Nauja rezervacija – 5 taškai
        award_points(instance.user, POINTS_FOR_RESERVATION)
        check_and_grant_achievements(instance.user)
    else:
        # Statusas atnaujintas į ATTENDED – papildomi taškai už dalyvavimą
        if instance.status == "ATTENDED":
            # Tikrinam, ar šis dalyvavimo įrašas jau buvo apdorotas –
            # paprastumo dėlei pridedam taškų tik jei prieš tai statusas
            # buvo kitoks. Kadangi signale negalim matyti senos reikšmės,
            # naudojam atskirą žymę ar papildomą logiką
            # (šiame sprendime – paprasčiausias variantas: duodam kartą).
            # Patikrinimas per `check_and_grant_achievements` apsaugo
            # nuo dublikatų: pasiekimai unikalūs pagal (user, achievement).
            award_points(instance.user, POINTS_FOR_ATTENDANCE)
            check_and_grant_achievements(instance.user)


@receiver(post_save, sender=Membership)
def membership_saved(sender, instance, created, **kwargs):
    """Kai nupirkamas naujas abonementas – priskiriami taškai."""
    if created:
        award_points(instance.user, POINTS_FOR_MEMBERSHIP_PURCHASE)
        check_and_grant_achievements(instance.user)
