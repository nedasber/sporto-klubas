"""
Management komanda – siunčia automatinius email priminimus.

Paleidimas:
    python manage.py send_reminders

Logika:
- Treniruotės priminimas DIENA prieš: visoms BOOKED rezervacijoms, kurių
  treniruotė vyksta per artimiausias 24h ± 30 min (t.y. ~rytojaus diena)
- Treniruotės priminimas 1 VALANDA prieš: kurios prasidės per 30-90 min
- Abonementas baigiasi: aktyvūs abonementai, baigsiantys per 7 d.

Naudojama Windows Task Scheduler arba cron'u (kasdien + kas valandą).
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from gym.models import Reservation, Membership
from accounts.emails import (
    send_training_reminder,
    send_membership_expiring,
)

class Command(BaseCommand):
    help = "Siunčia priminimus apie treniruotes ir abonemento pabaigą"

    def handle(self, *args, **options):
        now = timezone.now()

        self.stdout.write(self.style.NOTICE(f"[{now}] Pradedam siuntimą..."))

        # ---------------------------------------------------------------
        # 1. PRIMINIMAS DIENĄ PRIEŠ (24h ± 30 min langas)
        # ---------------------------------------------------------------
        day_start = now + timedelta(hours=23, minutes=30)
        day_end = now + timedelta(hours=24, minutes=30)

        day_reservations = Reservation.objects.filter(
            status="BOOKED",
            training__status="SCHEDULED",
            training__starts_at__gte=day_start,
            training__starts_at__lte=day_end,
        ).select_related("user", "training")

        sent_day = 0
        for res in day_reservations:
            if send_training_reminder(res, reminder_type="day"):
                sent_day += 1
                self.stdout.write(f"  [day] -> {res.user.email}: {res.training.title}")

        self.stdout.write(self.style.SUCCESS(f"Priminimų dieną prieš: {sent_day}"))

        # ---------------------------------------------------------------
        # 2. PRIMINIMAS 1 VAL. PRIEŠ (30-90 min langas)
        # ---------------------------------------------------------------
        hour_start = now + timedelta(minutes=30)
        hour_end = now + timedelta(minutes=90)

        hour_reservations = Reservation.objects.filter(
            status="BOOKED",
            training__status="SCHEDULED",
            training__starts_at__gte=hour_start,
            training__starts_at__lte=hour_end,
        ).select_related("user", "training")

        sent_hour = 0
        for res in hour_reservations:
            if send_training_reminder(res, reminder_type="hour"):
                sent_hour += 1
                self.stdout.write(f"  [hour] -> {res.user.email}: {res.training.title}")

        self.stdout.write(self.style.SUCCESS(f"Priminimų val. prieš: {sent_hour}"))

        # ---------------------------------------------------------------
        # 3. ABONEMENTAS BAIGIASI per 7 d. (vienkartinis)
        # ---------------------------------------------------------------
        today = now.date()
        cutoff = today + timedelta(days=7)

        expiring = Membership.objects.filter(
            status="ACTIVE",
            end_date__gte=today,
            end_date__lte=cutoff,
        ).select_related("user", "plan")

        sent_exp = 0
        for m in expiring:
            days_left = (m.end_date - today).days
            if send_membership_expiring(m, days_left):
                sent_exp += 1
                self.stdout.write(f"  [expiring] -> {m.user.email}: {m.plan.name} ({days_left}d)")

        self.stdout.write(self.style.SUCCESS(f"Abonementų pranešimų: {sent_exp}"))

        # ---------------------------------------------------------------
        total = sent_day + sent_hour + sent_exp
        self.stdout.write(self.style.SUCCESS(f"\n=== Iš viso išsiųsta: {total} laiškų ==="))
