from django.contrib.auth.models import User
from accounts.models import Profile


def create_test_users():
    print("=== SEED START ===")

    users_data = [
        {
            "username": "admin",
            "email": "admin@test.com",
            "password": "Admin123!",
            "role": "CLIENT",
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
            username=user_data["username"]
        )

        user.email = user_data["email"]
        user.is_staff = user_data["is_staff"]
        user.is_superuser = user_data["is_superuser"]
        user.set_password(user_data["password"])
        user.save()

        profile, profile_created = Profile.objects.get_or_create(user=user)
        profile.role = user_data["role"]
        profile.save()

        print(
            f"User={user.username}, created={created}, "
            f"profile_created={profile_created}, "
            f"password_ok={user.check_password(user_data['password'])}, "
            f"role={profile.role}"
        )

    print("All users in DB:", list(User.objects.values_list("username", flat=True)))
    print("=== SEED END ===")