"""
Signalai, kurie automatiškai prideda taškus, atnaujina streak'us ir tikrina pasiekimus.
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

from gym.models import Reservation, Membership
from .services import (
    award_points,
    check_and_grant_achievements,
    get_or_create_progress,
    POINTS_FOR_ATTENDANCE,
    POINTS_FOR_MEMBERSHIP_PURCHASE,
    POINTS_FOR_RESERVATION,
)


# SVARBU: cache, kad galetume sekti, ar status TIKRAI pasikeite is non-ATTENDED i ATTENDED.
# Tai apsauga nuo dvigubu tasku - jei treneris pazymes ATTENDED -> NO_SHOW -> ATTENDED,
# taskai bus skirti tik PIRMA karta.
_reservation_status_cache = {}


@receiver(pre_save, sender=Reservation)
def _track_reservation_status_before(sender, instance, **kwargs):
    """Isimena senaji rezervacijos status pries save'inant."""
    if instance.pk:
        try:
            old = Reservation.objects.get(pk=instance.pk)
            _reservation_status_cache[instance.pk] = old.status
        except Reservation.DoesNotExist:
            _reservation_status_cache[instance.pk] = None


@receiver(post_save, sender=Reservation)
def reservation_saved(sender, instance, created, **kwargs):
    if created:
        # Nauja rezervacija - skiriam +5 tasku
        award_points(instance.user, POINTS_FOR_RESERVATION)
        check_and_grant_achievements(instance.user)
        return

    # Update'as - tikrinam, ar TIKRAI pakeistas i ATTENDED is kito statuso
    old_status = _reservation_status_cache.pop(instance.pk, None)

    # Apsauga nuo dvigubu tasku: skiriam +10 tik jei status PIRMA karta tapo ATTENDED
    if instance.status == "ATTENDED" and old_status != "ATTENDED":
        progress = get_or_create_progress(instance.user)
        attendance_date = instance.training.starts_at.date()
        progress.update_streak(attendance_date)

        award_points(instance.user, POINTS_FOR_ATTENDANCE)
        check_and_grant_achievements(instance.user)


# Trackinam membership status pries save
_membership_status_cache = {}


@receiver(pre_save, sender=Membership)
def _track_membership_status_before(sender, instance, **kwargs):
    """Isimena senaji membership status pries save'inant (apsauga nuo dvigubu tasku)."""
    if instance.pk:
        try:
            old = Membership.objects.get(pk=instance.pk)
            _membership_status_cache[instance.pk] = old.status
        except Membership.DoesNotExist:
            _membership_status_cache[instance.pk] = None


@receiver(post_save, sender=Membership)
def membership_saved(sender, instance, created, **kwargs):
    """Skiriam +50 tasku tik UZ NAUJA membership, ne uz update'a."""
    if created:
        award_points(instance.user, POINTS_FOR_MEMBERSHIP_PURCHASE)
        check_and_grant_achievements(instance.user)
    else:
        # Update'as - nelieciam, kad nebutu dvigubu tasku
        _membership_status_cache.pop(instance.pk, None)
