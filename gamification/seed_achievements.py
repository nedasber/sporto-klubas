"""
Pradinių pasiekimų užkrovimo skriptas.
Paleidimas: python manage.py shell < gamification/seed_achievements.py
"""
from gamification.models import Achievement
from gamification.services import DEFAULT_ACHIEVEMENTS


def seed():
    created_count = 0
    for item in DEFAULT_ACHIEVEMENTS:
        obj, created = Achievement.objects.update_or_create(
            code=item["code"],
            defaults={
                "name": item["name"],
                "description": item["description"],
                "icon": item["icon"],
                "points_reward": item["points_reward"],
            },
        )
        if created:
            created_count += 1
            print(f"Sukurta: {obj.name}")
        else:
            print(f"Atnaujinta: {obj.name}")
    print(f"\nIš viso: {Achievement.objects.count()} pasiekimai. Naujų: {created_count}")


if __name__ == "__main__":
    seed()
else:
    seed()
