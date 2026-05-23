"""
Sporto klubo administracinė panelė.
Pasiekiama URL /manage/, tik staff vartotojams.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import timedelta

from accounts.models import Profile, EmailLog
from gym.models import (
    MembershipPlan, Membership, MembershipPurchase,
    Training, Reservation
)
from gamification.models import UserProgress, Achievement, UserAchievement


# ---------------------------------------------------------
# DEKORATORIUS - tik staff'ams
# ---------------------------------------------------------
def staff_required(view_func):
    """Leidžia tik prisijungusiems staff vartotojams."""
    decorated = user_passes_test(
        lambda u: u.is_authenticated and u.is_staff,
        login_url="/login/",
    )(view_func)
    return decorated


# ---------------------------------------------------------
# PAGRINDINIS PUSLAPIS - dashboard su statistika
# ---------------------------------------------------------
@staff_required
def dashboard(request):
    now = timezone.now()
    today = now.date()
    month_ago = today - timedelta(days=30)

    # Vartotojų statistika
    total_users = User.objects.count()
    clients = Profile.objects.filter(role="CLIENT").count()
    trainers = Profile.objects.filter(role="TRAINER").count()
    new_users_30d = User.objects.filter(date_joined__gte=month_ago).count()

    # Treniruočių statistika
    total_trainings = Training.objects.count()
    upcoming_trainings = Training.objects.filter(
        starts_at__gte=now, status="SCHEDULED"
    ).count()
    cancelled_trainings = Training.objects.filter(status="CANCELLED").count()

    # Rezervacijos
    total_reservations = Reservation.objects.count()
    active_reservations = Reservation.objects.filter(
        status="BOOKED", training__starts_at__gte=now
    ).count()

    # Narystės
    active_memberships = Membership.objects.filter(status="ACTIVE").count()
    expired_memberships = Membership.objects.filter(status="EXPIRED").count()

    # Pirkimai - suma
    paid_purchases = MembershipPurchase.objects.filter(status="PAID")
    total_revenue = sum(p.plan.price for p in paid_purchases)
    purchases_30d = paid_purchases.filter(created_at__gte=month_ago).count()

    # Paskutinės registracijos
    recent_users = User.objects.order_by("-date_joined")[:5]

    # Šios dienos treniruotės
    today_trainings = Training.objects.filter(
        starts_at__date=today, status="SCHEDULED"
    ).order_by("starts_at")[:5]

    context = {
        "section": "dashboard",
        "stats": {
            "total_users": total_users,
            "clients": clients,
            "trainers": trainers,
            "new_users_30d": new_users_30d,
            "total_trainings": total_trainings,
            "upcoming_trainings": upcoming_trainings,
            "cancelled_trainings": cancelled_trainings,
            "total_reservations": total_reservations,
            "active_reservations": active_reservations,
            "active_memberships": active_memberships,
            "expired_memberships": expired_memberships,
            "total_revenue": total_revenue,
            "purchases_30d": purchases_30d,
        },
        "recent_users": recent_users,
        "today_trainings": today_trainings,
    }
    return render(request, "manage/dashboard.html", context)


# ---------------------------------------------------------
# VARTOTOJAI
# ---------------------------------------------------------
@staff_required
def users_list(request):
    qs = User.objects.select_related("profile").order_by("-date_joined")

    # Paieška
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(username__icontains=q) | Q(email__icontains=q) |
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )

    # Filtras pagal rolę
    role = request.GET.get("role", "")
    if role in ("CLIENT", "TRAINER"):
        qs = qs.filter(profile__role=role)
    elif role == "STAFF":
        qs = qs.filter(is_staff=True)

    return render(request, "manage/users_list.html", {
        "section": "users",
        "users": qs,
        "q": q,
        "role": role,
    })


@staff_required
def user_create(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        role = request.POST.get("role", "CLIENT")
        is_staff = request.POST.get("is_staff") == "on"

        if not username or not password:
            messages.error(request, "Vartotojo vardas ir slaptažodis privalomi.")
            return redirect("/manage/users/create/")

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Vartotojas '{username}' jau egzistuoja.")
            return redirect("/manage/users/create/")

        if len(password) < 8:
            messages.error(request, "Slaptažodis turi būti bent 8 simbolių ilgio.")
            return redirect("/manage/users/create/")

        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        user.is_staff = is_staff
        if is_staff:
            user.is_superuser = True
        user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = role
        profile.email_verified = True  # Admin sukurta - patvirtinta iš karto
        profile.save()

        messages.success(request, f"Vartotojas '{username}' sėkmingai sukurtas.")
        return redirect("/manage/users/")

    return render(request, "manage/user_form.html", {
        "section": "users",
        "user_obj": None,
        "is_edit": False,
    })


@staff_required
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile, _ = Profile.objects.get_or_create(user=user)

    if request.method == "POST":
        user.email = request.POST.get("email", "").strip()
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name = request.POST.get("last_name", "").strip()
        user.is_active = request.POST.get("is_active") == "on"
        user.is_staff = request.POST.get("is_staff") == "on"

        # Slaptažodis - keičiamas tik jei įvestas
        new_password = request.POST.get("password", "").strip()
        if new_password:
            if len(new_password) < 8:
                messages.error(request, "Slaptažodis turi būti bent 8 simbolių ilgio.")
                return redirect(f"/manage/users/{user_id}/edit/")
            user.set_password(new_password)

        user.save()

        # Profile
        profile.role = request.POST.get("role", "CLIENT")
        profile.email_verified = request.POST.get("email_verified") == "on"
        profile.save()

        messages.success(request, f"Vartotojas '{user.username}' atnaujintas.")
        return redirect("/manage/users/")

    return render(request, "manage/user_form.html", {
        "section": "users",
        "user_obj": user,
        "profile": profile,
        "is_edit": True,
    })


@staff_required
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        messages.error(request, "Negalite ištrinti savo paskyros.")
        return redirect("/manage/users/")

    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, f"Vartotojas '{username}' ištrintas.")
        return redirect("/manage/users/")

    return render(request, "manage/confirm_delete.html", {
        "section": "users",
        "object": user,
        "object_name": user.username,
        "back_url": "/manage/users/",
    })


# ---------------------------------------------------------
# TRENIRUOTĖS
# ---------------------------------------------------------
@staff_required
def trainings_list(request):
    qs = Training.objects.select_related("trainer").order_by("-starts_at")

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(title__icontains=q)

    status = request.GET.get("status", "")
    if status in ("SCHEDULED", "CANCELLED"):
        qs = qs.filter(status=status)

    return render(request, "manage/trainings_list.html", {
        "section": "trainings",
        "trainings": qs,
        "q": q,
        "status": status,
        "now": timezone.now(),
    })


@staff_required
def training_delete(request, training_id):
    training = get_object_or_404(Training, id=training_id)

    if request.method == "POST":
        title = training.title
        training.delete()
        messages.success(request, f"Treniruotė '{title}' ištrinta.")
        return redirect("/manage/trainings/")

    return render(request, "manage/confirm_delete.html", {
        "section": "trainings",
        "object": training,
        "object_name": training.title,
        "back_url": "/manage/trainings/",
    })


# ---------------------------------------------------------
# ABONEMENTŲ PLANAI
# ---------------------------------------------------------
@staff_required
def plans_list(request):
    plans = MembershipPlan.objects.order_by("price")
    return render(request, "manage/plans_list.html", {
        "section": "plans",
        "plans": plans,
    })


@staff_required
def plan_create(request):
    if request.method == "POST":
        try:
            MembershipPlan.objects.create(
                name=request.POST.get("name", "").strip(),
                duration_days=int(request.POST.get("duration_days", 30)),
                visit_limit=int(request.POST.get("visit_limit") or 0) or None,
                price=float(request.POST.get("price", 0)),
            )
            messages.success(request, "Planas sukurtas.")
            return redirect("/manage/plans/")
        except (ValueError, TypeError):
            messages.error(request, "Neteisingi duomenys. Patikrinkite skaitines reikšmes.")

    return render(request, "manage/plan_form.html", {
        "section": "plans",
        "plan": None,
        "is_edit": False,
    })


@staff_required
def plan_edit(request, plan_id):
    plan = get_object_or_404(MembershipPlan, id=plan_id)

    if request.method == "POST":
        try:
            plan.name = request.POST.get("name", "").strip()
            plan.duration_days = int(request.POST.get("duration_days", 30))
            visit_limit = int(request.POST.get("visit_limit") or 0)
            plan.visit_limit = visit_limit if visit_limit > 0 else None
            plan.price = float(request.POST.get("price", 0))
            plan.save()
            messages.success(request, f"Planas '{plan.name}' atnaujintas.")
            return redirect("/manage/plans/")
        except (ValueError, TypeError):
            messages.error(request, "Neteisingi duomenys. Patikrinkite skaitines reikšmes.")

    return render(request, "manage/plan_form.html", {
        "section": "plans",
        "plan": plan,
        "is_edit": True,
    })


@staff_required
def plan_delete(request, plan_id):
    plan = get_object_or_404(MembershipPlan, id=plan_id)

    if request.method == "POST":
        try:
            name = plan.name
            plan.delete()
            messages.success(request, f"Planas '{name}' ištrintas.")
        except Exception as e:
            messages.error(request, f"Negalima ištrinti plano - jis naudojamas: {e}")
        return redirect("/manage/plans/")

    return render(request, "manage/confirm_delete.html", {
        "section": "plans",
        "object": plan,
        "object_name": plan.name,
        "back_url": "/manage/plans/",
    })


# ---------------------------------------------------------
# NARYSTĖS
# ---------------------------------------------------------
@staff_required
def memberships_list(request):
    qs = Membership.objects.select_related("user", "plan").order_by("-created_at")

    status = request.GET.get("status", "")
    if status in ("ACTIVE", "EXPIRED", "PAUSED"):
        qs = qs.filter(status=status)

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(user__username__icontains=q)

    return render(request, "manage/memberships_list.html", {
        "section": "memberships",
        "memberships": qs,
        "status": status,
        "q": q,
    })


@staff_required
def membership_change_status(request, membership_id, new_status):
    if new_status not in ("ACTIVE", "EXPIRED", "PAUSED"):
        return HttpResponseForbidden("Neteisingas statusas")

    membership = get_object_or_404(Membership, id=membership_id)
    membership.status = new_status
    membership.save()
    messages.success(request, f"Narystės statusas pakeistas į '{membership.get_status_display()}'.")
    return redirect("/manage/memberships/")


# ---------------------------------------------------------
# PIRKIMAI
# ---------------------------------------------------------
@staff_required
def purchases_list(request):
    qs = MembershipPurchase.objects.select_related("user", "plan").order_by("-created_at")

    status = request.GET.get("status", "")
    if status in ("PENDING", "PAID", "REJECTED"):
        qs = qs.filter(status=status)

    return render(request, "manage/purchases_list.html", {
        "section": "purchases",
        "purchases": qs,
        "status": status,
    })


# ---------------------------------------------------------
# PASIEKIMAI
# ---------------------------------------------------------
@staff_required
def achievements_list(request):
    achievements = Achievement.objects.order_by("points_reward")
    return render(request, "manage/achievements_list.html", {
        "section": "achievements",
        "achievements": achievements,
    })


@staff_required
def achievement_create(request):
    if request.method == "POST":
        try:
            Achievement.objects.create(
                code=request.POST.get("code", "").strip(),
                name=request.POST.get("name", "").strip(),
                description=request.POST.get("description", "").strip(),
                icon=request.POST.get("icon", "trophy").strip(),
                points_reward=int(request.POST.get("points_reward", 50)),
            )
            messages.success(request, "Pasiekimas sukurtas.")
            return redirect("/manage/achievements/")
        except (ValueError, TypeError) as e:
            messages.error(request, f"Klaida: {e}")

    return render(request, "manage/achievement_form.html", {
        "section": "achievements",
        "achievement": None,
        "is_edit": False,
    })


@staff_required
def achievement_edit(request, achievement_id):
    ach = get_object_or_404(Achievement, id=achievement_id)

    if request.method == "POST":
        try:
            ach.code = request.POST.get("code", "").strip()
            ach.name = request.POST.get("name", "").strip()
            ach.description = request.POST.get("description", "").strip()
            ach.icon = request.POST.get("icon", "trophy").strip()
            ach.points_reward = int(request.POST.get("points_reward", 50))
            ach.save()
            messages.success(request, f"Pasiekimas '{ach.name}' atnaujintas.")
            return redirect("/manage/achievements/")
        except (ValueError, TypeError) as e:
            messages.error(request, f"Klaida: {e}")

    return render(request, "manage/achievement_form.html", {
        "section": "achievements",
        "achievement": ach,
        "is_edit": True,
    })


@staff_required
def achievement_delete(request, achievement_id):
    ach = get_object_or_404(Achievement, id=achievement_id)

    if request.method == "POST":
        name = ach.name
        ach.delete()
        messages.success(request, f"Pasiekimas '{name}' ištrintas.")
        return redirect("/manage/achievements/")

    return render(request, "manage/confirm_delete.html", {
        "section": "achievements",
        "object": ach,
        "object_name": ach.name,
        "back_url": "/manage/achievements/",
    })


# ---------------------------------------------------------
# EL. LAIŠKŲ ŽURNALAS
# ---------------------------------------------------------
@staff_required
def email_log(request):
    qs = EmailLog.objects.select_related("user").order_by("-sent_at")[:200]

    kind = request.GET.get("kind", "")
    if kind:
        qs = EmailLog.objects.filter(kind=kind).select_related("user").order_by("-sent_at")[:200]

    kinds = EmailLog.KIND_CHOICES

    return render(request, "manage/email_log.html", {
        "section": "email_log",
        "logs": qs,
        "kind": kind,
        "kinds": kinds,
    })
