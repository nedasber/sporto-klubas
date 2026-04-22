"""
Motyvacinės sistemos verslo logika.
Čia apibrėžiama, už kokius veiksmus vartotojas gauna taškų ir pasiekimų.
"""
from django.db.models import Count, Q
from .models import UserProgress, Achievement, UserAchievement


# Taškų kiekiai už veiksmus
POINTS_FOR_ATTENDANCE = 10        # Dalyvavo treniruotėje
POINTS_FOR_MEMBERSHIP_PURCHASE = 50  # Nupirko abonementą
POINTS_FOR_RESERVATION = 5        # Užsiregistravo į treniruotę


def get_or_create_progress(user):
    """Grąžina (arba sukuria) vartotojo pažangos įrašą."""
    progress, _ = UserProgress.objects.get_or_create(user=user)
    return progress


def award_points(user, amount: int):
    """Prideda taškų vartotojui ir atnaujina jo lygį."""
    progress = get_or_create_progress(user)
    progress.add_points(amount)
    return progress


def grant_achievement(user, code: str):
    """
    Suteikia pasiekimą, jei vartotojas jo dar neturi.
    Grąžina (UserAchievement, created_flag) kortežą.
    """
    try:
        achievement = Achievement.objects.get(code=code)
    except Achievement.DoesNotExist:
        return None, False

    user_ach, created = UserAchievement.objects.get_or_create(
        user=user,
        achievement=achievement,
    )
    if created and achievement.points_reward > 0:
        award_points(user, achievement.points_reward)
    return user_ach, created


def check_and_grant_achievements(user):
    """
    Tikrina visus pasiekimus ir priskiria tuos, kurių kriterijai jau įvykdyti.
    Kviečiama po svarbių veiksmų (pirma rezervacija, abonemento pirkimas,
    lankomumo užfiksavimas ir pan.).
    Grąžina naujai gautų pasiekimų sąrašą.
    """
    from gym.models import Reservation, Membership

    newly_granted = []

    # Kiek treniruočių vartotojas aplankė
    attended_count = Reservation.objects.filter(
        user=user, status="ATTENDED"
    ).count()

    # Kiek rezervacijų iš viso padaryta
    booked_count = Reservation.objects.filter(
        user=user
    ).exclude(status="CANCELLED").count()

    # Kiek narysčių nupirkta iš viso
    membership_count = Membership.objects.filter(user=user).count()

    # 1. Pirmoji rezervacija
    if booked_count >= 1:
        _, created = grant_achievement(user, "first_reservation")
        if created:
            newly_granted.append("first_reservation")

    # 2. Pirmas dalyvavimas treniruotėje
    if attended_count >= 1:
        _, created = grant_achievement(user, "first_attendance")
        if created:
            newly_granted.append("first_attendance")

    # 3. Pirmas abonementas
    if membership_count >= 1:
        _, created = grant_achievement(user, "first_membership")
        if created:
            newly_granted.append("first_membership")

    # 4. 5 treniruotės
    if attended_count >= 5:
        _, created = grant_achievement(user, "five_attendances")
        if created:
            newly_granted.append("five_attendances")

    # 5. 10 treniruočių
    if attended_count >= 10:
        _, created = grant_achievement(user, "ten_attendances")
        if created:
            newly_granted.append("ten_attendances")

    # 6. 25 treniruotės
    if attended_count >= 25:
        _, created = grant_achievement(user, "twenty_five_attendances")
        if created:
            newly_granted.append("twenty_five_attendances")

    return newly_granted


# Pradinių pasiekimų sąrašas (naudojamas seed skripte)
DEFAULT_ACHIEVEMENTS = [
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
]
