"""
Motyvacinės sistemos verslo logika.
"""
from django.db.models import Count, Q
from .models import UserProgress, Achievement, UserAchievement


# Taškų kiekiai už veiksmus
POINTS_FOR_ATTENDANCE = 10
POINTS_FOR_MEMBERSHIP_PURCHASE = 50
POINTS_FOR_RESERVATION = 5


def get_or_create_progress(user):
    progress, _ = UserProgress.objects.get_or_create(user=user)
    return progress


def award_points(user, amount: int):
    progress = get_or_create_progress(user)
    progress.add_points(amount)
    return progress


def grant_achievement(user, code: str):
    try:
        achievement = Achievement.objects.get(code=code)
    except Achievement.DoesNotExist:
        return None, False

    user_ach, created = UserAchievement.objects.get_or_create(
        user=user, achievement=achievement,
    )
    if created and achievement.points_reward > 0:
        award_points(user, achievement.points_reward)
    return user_ach, created


def check_and_grant_achievements(user):
    """
    Tikrina visus pasiekimus ir priskiria tuos, kurių kriterijai jau įvykdyti.
    """
    from gym.models import Reservation, Membership

    newly_granted = []
    progress = get_or_create_progress(user)

    attended_count = Reservation.objects.filter(
        user=user, status="ATTENDED"
    ).count()

    booked_count = Reservation.objects.filter(
        user=user
    ).exclude(status="CANCELLED").count()

    membership_count = Membership.objects.filter(user=user).count()

    # Pasiekimų sąrašas: (code, condition)
    checks = [
        ("first_reservation", booked_count >= 1),
        ("first_attendance", attended_count >= 1),
        ("first_membership", membership_count >= 1),
        ("five_attendances", attended_count >= 5),
        ("ten_attendances", attended_count >= 10),
        ("twenty_five_attendances", attended_count >= 25),
        ("fifty_attendances", attended_count >= 50),

        # Streak'ai
        ("streak_3", progress.current_streak >= 3),
        ("streak_7", progress.current_streak >= 7),
        ("streak_14", progress.current_streak >= 14),
        ("streak_30", progress.current_streak >= 30),
    ]

    for code, condition in checks:
        if condition:
            _, created = grant_achievement(user, code)
            if created:
                newly_granted.append(code)

    return newly_granted


# Pradinių pasiekimų sąrašas (naudojamas seed skripte)
DEFAULT_ACHIEVEMENTS = [
    # Pirmieji žingsniai
    {
        "code": "first_reservation",
        "name": "Pirmas žingsnis",
        "description": "Užsiregistravote į pirmąją treniruotę",
        "icon": "bookmark-star-fill",
        "points_reward": 20,
    },
    {
        "code": "first_attendance",
        "name": "Pradžia padaryta",
        "description": "Dalyvavote pirmojoje treniruotėje",
        "icon": "flag-fill",
        "points_reward": 30,
    },
    {
        "code": "first_membership",
        "name": "Narys",
        "description": "Įsigijote pirmąjį abonementą",
        "icon": "credit-card-2-front-fill",
        "points_reward": 30,
    },

    # Dalyvavimų pasiekimai
    {
        "code": "five_attendances",
        "name": "Aktyvus sportininkas",
        "description": "Dalyvavote 5 treniruotėse",
        "icon": "lightning-charge-fill",
        "points_reward": 50,
    },
    {
        "code": "ten_attendances",
        "name": "Ištvermės meistras",
        "description": "Dalyvavote 10 treniruočių",
        "icon": "fire",
        "points_reward": 100,
    },
    {
        "code": "twenty_five_attendances",
        "name": "Tikras atletas",
        "description": "Dalyvavote 25 treniruotėse",
        "icon": "trophy-fill",
        "points_reward": 200,
    },
    {
        "code": "fifty_attendances",
        "name": "Sporto legenda",
        "description": "Dalyvavote 50 treniruočių",
        "icon": "gem",
        "points_reward": 400,
    },

    # Streak'ai
    {
        "code": "streak_3",
        "name": "Įgaunate pagreitį",
        "description": "Dalyvavote 3 dienas iš eilės",
        "icon": "arrow-up-circle-fill",
        "points_reward": 30,
    },
    {
        "code": "streak_7",
        "name": "Savaitės iššūkis",
        "description": "Dalyvavote 7 dienas iš eilės",
        "icon": "calendar-week-fill",
        "points_reward": 70,
    },
    {
        "code": "streak_14",
        "name": "Dviejų savaičių karys",
        "description": "Dalyvavote 14 dienų iš eilės",
        "icon": "shield-fill",
        "points_reward": 150,
    },
    {
        "code": "streak_30",
        "name": "Nesustabdomas",
        "description": "Dalyvavote 30 dienų iš eilės",
        "icon": "star-fill",
        "points_reward": 350,
    },
]
