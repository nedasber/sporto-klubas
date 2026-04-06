from django.contrib.auth.models import User
from accounts.models import Profile


def create_test_users():
    users_data = [
        {
            "username": "admin",
            "email": "admin@test.com",
            "password": "Admin123!",
            "role": "CLIENT",  # admin neturi specialios rolės pas tave
            "is_staff": True,
            "is_superuser": True,
        },
        {
            "username": "treneris",
            "email": "treneris@test.com",
            "password": "Treneris123!",
            "role": "TRAINER",
            "is_staff": False,
            "is_superuser": False,
        },
        {
            "username": "klientas",
            "email": "klientas@test.com",
            "password": "Klientas123!",
            "role": "CLIENT",
            "is_staff": False,
            "is_superuser": False,
        },
    ]

    for user_data in users_data:
        user, created = User.objects.get_or_create(
            username=user_data["username"],
            defaults={
                "email": user_data["email"],
                "is_staff": user_data["is_staff"],
                "is_superuser": user_data["is_superuser"],
            },
        )

        if created:
            user.set_password(user_data["password"])
            user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = user_data["role"]
        profile.save()