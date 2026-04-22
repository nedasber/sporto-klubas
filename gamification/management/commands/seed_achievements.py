"""
Management komanda: python manage.py seed_achievements

Sukuria arba atnaujina visus motyvacinės sistemos pasiekimus
pagal DEFAULT_ACHIEVEMENTS sąrašą iš services.py.
"""
from django.core.management.base import BaseCommand

from gamification.models import Achievement
from gamification.services import DEFAULT_ACHIEVEMENTS


class Command(BaseCommand):
    help = "Sukuria arba atnaujina numatytuosius pasiekimus."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for data in DEFAULT_ACHIEVEMENTS:
            obj, created = Achievement.objects.update_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "description": data["description"],
                    "icon": data["icon"],
                    "points_reward": data["points_reward"],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✔ Sukurta: {obj.name}"))
            else:
                updated_count += 1
                self.stdout.write(f"• Atnaujinta: {obj.name}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Baigta. Sukurta: {created_count}, atnaujinta: {updated_count}."
        ))