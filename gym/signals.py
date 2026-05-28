"""
Gym aplikacijos signalai – automatiškai siunčia email'us esant tam tikriems įvykiams.
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Training, Reservation


# Trackinam senąjį Training statusą, kad žinotume, ar jis ką tik pakeistas į CANCELLED
_training_status_cache = {}


@receiver(pre_save, sender=Training)
def _track_training_status_before(sender, instance, **kwargs):
    """Įsimena senąjį statusą prieš save'inant."""
    if instance.pk:
        try:
            old = Training.objects.get(pk=instance.pk)
            _training_status_cache[instance.pk] = old.status
        except Training.DoesNotExist:
            _training_status_cache[instance.pk] = None


@receiver(post_save, sender=Training)
def _send_cancellation_emails(sender, instance, created, **kwargs):
    """Jei treniruotės statusas ką tik pakeistas į CANCELLED – siunčia laiškus."""
    if created:
        _training_status_cache.pop(instance.pk, None)
        return

    old_status = _training_status_cache.pop(instance.pk, None)

    # Tik jei buvo NE-cancelled, dabar tapo CANCELLED
    if old_status != "CANCELLED" and instance.status == "CANCELLED":
        # SVARBU: nustatom cancelled_at, kad varpelio pranesimai galetu filtruoti
        # pagal sia data. Naudojam update_fields, kad nepaleistume signal'o vel.
        from django.utils import timezone
        Training.objects.filter(pk=instance.pk).update(cancelled_at=timezone.now())

        from accounts.emails import send_training_cancelled

        # Visiems aktyviems rezervuotojams
        active_reservations = Reservation.objects.filter(
            training=instance,
            status="BOOKED",
        ).select_related("user")

        for res in active_reservations:
            try:
                send_training_cancelled(res)
            except Exception as exc:
                print(f"[signal] Failed to send cancellation: {exc}")
