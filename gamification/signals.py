"""
Signalai, kurie automatiškai prideda taškus, atnaujina streak'us ir tikrina pasiekimus.
"""
from django.db.models.signals import post_save
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


@receiver(post_save, sender=Reservation)
def reservation_saved(sender, instance, created, **kwargs):
    if created:
        award_points(instance.user, POINTS_FOR_RESERVATION)
        check_and_grant_achievements(instance.user)
    else:
        if instance.status == "ATTENDED":
            # Atnaujinam streak'ą pagal treniruotės datą
            progress = get_or_create_progress(instance.user)
            attendance_date = instance.training.starts_at.date()
            progress.update_streak(attendance_date)

            award_points(instance.user, POINTS_FOR_ATTENDANCE)
            check_and_grant_achievements(instance.user)


@receiver(post_save, sender=Membership)
def membership_saved(sender, instance, created, **kwargs):
    if created:
        award_points(instance.user, POINTS_FOR_MEMBERSHIP_PURCHASE)
        check_and_grant_achievements(instance.user)
