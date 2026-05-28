from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Profile

User = get_user_model()


class Command(BaseCommand):
    help = "Pataiso egzistuojančius admin vartotojus - priskiria ADMIN rolę"

    def handle(self, *args, **options):
        # Surandam visus superuser/staff vartotojus
        admin_users = User.objects.filter(is_superuser=True) | User.objects.filter(is_staff=True)
        admin_users = admin_users.distinct()

        updated_count = 0
        created_count = 0

        for user in admin_users:
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={"role": "ADMIN"}
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Sukurtas profilis: {user.username} -> ADMIN"
                ))
            elif profile.role != "ADMIN":
                old_role = profile.role
                profile.role = "ADMIN"
                profile.save(update_fields=["role"])
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Atnaujinta: {user.username} ({old_role} -> ADMIN)"
                ))
            else:
                self.stdout.write(
                    f"Jau ADMIN: {user.username}"
                )

        self.stdout.write(self.style.SUCCESS(
            f"\nBaigta. Sukurta: {created_count}, atnaujinta: {updated_count}"
        ))