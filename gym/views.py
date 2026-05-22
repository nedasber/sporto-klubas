from datetime import timedelta

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from accounts.models import Profile
from gamification.models import UserAchievement
from gamification.services import get_or_create_progress
from .forms import MembershipPurchaseForm, TrainingForm
from .models import Membership, MembershipPlan, MembershipPurchase, Reservation, Training

stripe.api_key = settings.STRIPE_SECRET_KEY


def _has_active_membership(user) -> bool:
    today = timezone.now().date()
    return Membership.objects.filter(
        user=user,
        status="ACTIVE",
        start_date__lte=today,
        end_date__gte=today,
    ).exists()


def _activate_membership_from_purchase(purchase: MembershipPurchase) -> Membership:
    """Pagal apmokėtą MembershipPurchase sukuria aktyvią Membership."""
    plan = purchase.plan
    start = timezone.now().date()
    end = start + timedelta(days=plan.duration_days)
    visits_left = plan.visit_limit if plan.visit_limit else None

    membership = Membership.objects.create(
        user=purchase.user,
        plan=plan,
        start_date=start,
        end_date=end,
        status="ACTIVE",
        visits_left=visits_left,
    )

    # Siunčiam patvirtinimo laišką
    try:
        from accounts.emails import send_membership_purchased
        send_membership_purchased(membership)
    except Exception as exc:
        print(f"[membership purchase] Email send failed: {exc}")

    return membership


def _trainer_dashboard(request):
    """Atskirai parengtas dashboard'as treneriui – kalendorius, statistika, artimiausios treniruotės."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    week_end = today_start + timedelta(days=7)
    month_start = today_start.replace(day=1)

    # --- ŠIANDIENOS TRENIRUOTĖS (kalendoriaus eilutės) ---
    today_trainings = list(
        Training.objects.filter(
            trainer=request.user,
            starts_at__gte=today_start,
            starts_at__lt=today_end,
        )
        .annotate(booked_count=Count("reservations", filter=Q(reservations__status="BOOKED")))
        .order_by("starts_at")
    )

    # --- ARTIMIAUSIOS 7 DIENOS ---
    upcoming_week = list(
        Training.objects.filter(
            trainer=request.user,
            starts_at__gte=now,
            starts_at__lt=week_end,
        )
        .annotate(booked_count=Count("reservations", filter=Q(reservations__status="BOOKED")))
        .order_by("starts_at")[:10]
    )
    # Užimtumo procentas kiekvienai treniruotei
    for t in upcoming_week:
        t.fill_percent = int((t.booked_count / t.capacity) * 100) if t.capacity else 0

    # --- STATISTIKOS ---
    # Šiandien treniruočių sk.
    today_count = len(today_trainings)

    # Šios savaitės dalyvių iš viso (rezervacijų sk., BOOKED + ATTENDED)
    week_attendees = Reservation.objects.filter(
        training__trainer=request.user,
        training__starts_at__gte=today_start,
        training__starts_at__lt=week_end,
        status__in=["BOOKED", "ATTENDED"],
    ).count()

    # Šio mėnesio užimtumas (vidurkis)
    month_trainings = Training.objects.filter(
        trainer=request.user,
        starts_at__gte=month_start,
        starts_at__lt=today_end,
        status="SCHEDULED",
    ).annotate(
        booked_count=Count("reservations", filter=Q(reservations__status__in=["BOOKED", "ATTENDED"]))
    )
    total_capacity = sum(t.capacity for t in month_trainings)
    total_booked = sum(t.booked_count for t in month_trainings)
    month_fill_percent = int((total_booked / total_capacity) * 100) if total_capacity else 0

    # Aktyvios treniruotės iš viso (būsimos, planuojamos)
    active_count = Training.objects.filter(
        trainer=request.user,
        starts_at__gte=now,
        status="SCHEDULED",
    ).count()

    stats = {
        "today_count": today_count,
        "week_attendees": week_attendees,
        "month_fill_percent": month_fill_percent,
        "active_count": active_count,
    }

    return render(request, "gym/trainer_dashboard.html", {
        "today_trainings": today_trainings,
        "upcoming_week": upcoming_week,
        "stats": stats,
        "now": now,
    })


@login_required
def dashboard(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"role": "CLIENT"},
    )

    # Treneris turi savo atskirą dashboard'ą
    if profile.role == "TRAINER":
        return _trainer_dashboard(request)

    today = timezone.now().date()

    membership = (
        Membership.objects.filter(
            user=request.user,
            status="ACTIVE",
            start_date__lte=today,
            end_date__gte=today,
        )
        .select_related("plan")
        .order_by("-end_date")
        .first()
    )

    membership_info = None
    if membership:
        total_days = max((membership.end_date - membership.start_date).days, 1)
        elapsed_days = (today - membership.start_date).days
        elapsed_days = min(max(elapsed_days, 0), total_days)

        time_progress = int((elapsed_days / total_days) * 100)
        days_left = max((membership.end_date - today).days, 0)

        visit_limit = membership.plan.visit_limit
        visits_left = membership.visits_left

        visit_progress = 0
        if visit_limit:
            if visits_left is None:
                visits_left = visit_limit
            used = max(visit_limit - visits_left, 0)
            visit_progress = int((used / visit_limit) * 100)

        membership_info = {
            "obj": membership,
            "days_left": days_left,
            "time_progress": time_progress,
            "visit_limit": visit_limit,
            "visits_left": visits_left,
            "visit_progress": visit_progress,
        }

    stats = {
        "booked": Reservation.objects.filter(user=request.user, status="BOOKED").count(),
        "cancelled": Reservation.objects.filter(user=request.user, status="CANCELLED").count(),
        "attended": Reservation.objects.filter(user=request.user, status="ATTENDED").count(),
        "no_show": Reservation.objects.filter(user=request.user, status="NO_SHOW").count(),
    }

    upcoming = (
        Reservation.objects.filter(
            user=request.user,
            status="BOOKED",
            training__starts_at__gte=timezone.now(),
        )
        .select_related("training", "training__trainer")
        .order_by("training__starts_at")[:5]
    )

    progress = get_or_create_progress(request.user)
    recent_achievements = UserAchievement.objects.filter(
        user=request.user
    ).select_related("achievement")[:6]

    gamification_info = {
        "points": progress.points,
        "level": progress.level,
        "level_name": progress.get_level_display(),
        "progress_percent": progress.progress_to_next_level(),
        "points_to_next": progress.points_to_next_level(),
        "achievements": recent_achievements,
        "achievements_count": UserAchievement.objects.filter(user=request.user).count(),
        "current_streak": progress.current_streak,
        "longest_streak": progress.longest_streak,
    }

    # Mini leaderboard – Top 5 + dabartinio vartotojo pozicija
    from gamification.models import UserProgress
    from accounts.models import Profile as ProfileModel
    client_profile_ids = ProfileModel.objects.filter(role="CLIENT").values_list("user_id", flat=True)

    top_users = list(
        UserProgress.objects.filter(user_id__in=client_profile_ids)
        .select_related("user")
        .order_by("-points")[:5]
    )
    for i, p in enumerate(top_users, start=1):
        p.rank = i

    # Mano pozicija
    my_position = None
    if profile.role == "CLIENT":
        higher_count = UserProgress.objects.filter(
            user_id__in=client_profile_ids,
            points__gt=progress.points,
        ).count()
        my_position = higher_count + 1

    leaderboard_widget = {
        "top_users": top_users,
        "my_position": my_position,
    }

    return render(request, "gym/dashboard.html", {
        "role": profile.role,
        "membership_info": membership_info,
        "stats": stats,
        "upcoming": upcoming,
        "gamification_info": gamification_info,
        "leaderboard_widget": leaderboard_widget,
    })


@login_required
def achievements_page(request):
    """Visų lygių ir pasiekimų puslapis."""
    from gamification.models import UserProgress, Achievement, UserAchievement

    progress = UserProgress.objects.get_or_create(user=request.user)[0]

    all_achievements = Achievement.objects.all().order_by("points_reward")
    earned_codes = set(
        UserAchievement.objects.filter(user=request.user).values_list("achievement__code", flat=True)
    )

    achievements_data = []
    for ach in all_achievements:
        achievements_data.append({
            "obj": ach,
            "earned": ach.code in earned_codes,
        })

    levels_info = []
    for level_num, threshold in progress.LEVEL_THRESHOLDS.items():
        level_name = dict(progress.LEVEL_CHOICES).get(level_num, "")
        if level_num < 5:
            next_threshold = progress.LEVEL_THRESHOLDS[level_num + 1]
            points_range = f"{threshold} – {next_threshold - 1}"
        else:
            points_range = f"{threshold}+"

        levels_info.append({
            "num": level_num,
            "name": level_name,
            "threshold": threshold,
            "points_range": points_range,
            "is_current": progress.level == level_num,
            "is_reached": progress.points >= threshold,
        })

    from gamification.services import (
        POINTS_FOR_RESERVATION,
        POINTS_FOR_ATTENDANCE,
        POINTS_FOR_MEMBERSHIP_PURCHASE,
    )

    point_rules = [
        {"action": "Užsiregistruoti į treniruotę", "points": POINTS_FOR_RESERVATION, "icon": "bookmark-check"},
        {"action": "Dalyvauti treniruotėje", "points": POINTS_FOR_ATTENDANCE, "icon": "check-circle"},
        {"action": "Įsigyti abonementą", "points": POINTS_FOR_MEMBERSHIP_PURCHASE, "icon": "credit-card-2-front"},
    ]

    return render(request, "gym/achievements.html", {
        "progress": progress,
        "achievements_data": achievements_data,
        "earned_count": len(earned_codes),
        "total_count": all_achievements.count(),
        "levels_info": levels_info,
        "point_rules": point_rules,
    })


@login_required
def mark_notifications_seen(request):
    """Pažymi visus pranešimus perskaitytais (atnaujina last_notifications_seen_at)."""
    from django.http import JsonResponse
    profile = request.user.profile
    profile.last_notifications_seen_at = timezone.now()
    profile.save(update_fields=["last_notifications_seen_at"])
    return JsonResponse({"ok": True})


@login_required
def leaderboard(request):
    """Lyderių lentelė – rikiavimas pagal taškus."""
    from gamification.models import UserProgress
    from accounts.models import Profile

    filter_mode = request.GET.get("filter", "all").strip()

    client_profiles = Profile.objects.filter(role="CLIENT").values_list("user_id", flat=True)
    qs = UserProgress.objects.filter(
        user_id__in=client_profiles
    ).select_related("user").order_by("-points")

    if filter_mode == "active":
        cutoff = timezone.now().date() - timedelta(days=30)
        qs = qs.filter(last_attendance_date__gte=cutoff)
    elif filter_mode == "inactive":
        cutoff = timezone.now().date() - timedelta(days=30)
        qs = qs.exclude(last_attendance_date__gte=cutoff)

    leaderboard_list = list(qs[:100])

    for i, progress in enumerate(leaderboard_list, start=1):
        progress.rank = i
        progress.is_active = progress.is_active_member()

    my_position = None
    my_progress = None
    if request.user.is_authenticated:
        try:
            my_progress = UserProgress.objects.get(user=request.user)
            higher_count = UserProgress.objects.filter(
                user_id__in=client_profiles,
                points__gt=my_progress.points,
            ).count()
            my_position = higher_count + 1
            my_progress.is_active = my_progress.is_active_member()
        except UserProgress.DoesNotExist:
            pass

    return render(request, "gym/leaderboard.html", {
        "leaderboard": leaderboard_list,
        "my_position": my_position,
        "my_progress": my_progress,
        "filter_mode": filter_mode,
        "total_count": qs.count(),
    })


def trainings_list(request):
    trainings_qs = (
        Training.objects.filter(starts_at__gte=timezone.now())
        .annotate(
            booked_count=Count("reservations", filter=Q(reservations__status="BOOKED"))
        )
    )

    # --- FILTRAI ---
    # Paieška pagal pavadinimą
    search_query = request.GET.get("q", "").strip()
    if search_query:
        trainings_qs = trainings_qs.filter(title__icontains=search_query)

    # Filtravimas pagal dieną (data formatu YYYY-MM-DD)
    date_filter = request.GET.get("date", "").strip()
    if date_filter:
        try:
            from datetime import datetime as _dt
            day = _dt.strptime(date_filter, "%Y-%m-%d").date()
            trainings_qs = trainings_qs.filter(starts_at__date=day)
        except ValueError:
            date_filter = ""

    # Filtravimas pagal valandą
    # ranges: morning (06-12), afternoon (12-17), evening (17-22)
    time_filter = request.GET.get("time", "").strip()
    if time_filter == "morning":
        trainings_qs = trainings_qs.filter(starts_at__hour__gte=6, starts_at__hour__lt=12)
    elif time_filter == "afternoon":
        trainings_qs = trainings_qs.filter(starts_at__hour__gte=12, starts_at__hour__lt=17)
    elif time_filter == "evening":
        trainings_qs = trainings_qs.filter(starts_at__hour__gte=17, starts_at__hour__lt=22)

    # Filtravimas pagal tipą
    type_filter = request.GET.get("type", "").strip()
    if type_filter:
        trainings_qs = trainings_qs.filter(title=type_filter)

    # Tik tos, kuriose dar yra vietos (checkbox)
    only_available = request.GET.get("available") == "1"

    # Rikiavimas
    sort_order = request.GET.get("sort", "asc").strip()
    if sort_order == "desc":
        trainings_qs = trainings_qs.order_by("-starts_at")
    else:
        trainings_qs = trainings_qs.order_by("starts_at")
        sort_order = "asc"

    trainings = []
    for t in trainings_qs:
        t.left_count = max(t.capacity - t.booked_count, 0)
        t.is_full = (t.left_count <= 0)
        if only_available and t.is_full:
            continue  # praleidžiam pilnas, jei pažymėtas filtras
        trainings.append(t)

    my_booked_ids = set()
    if request.user.is_authenticated:
        my_booked_ids = set(
            Reservation.objects.filter(
                user=request.user,
                status="BOOKED",
                training__in=trainings_qs,
            ).values_list("training_id", flat=True)
        )

    # Sąrašas tipų – iš formų konstantos
    from .forms import TRAINING_TYPE_CHOICES
    type_choices = [(v, l) for v, l in TRAINING_TYPE_CHOICES if v]  # be tuščio

    return render(request, "gym/trainings_list.html", {
        "trainings": trainings,
        "my_booked_ids": my_booked_ids,
        "search_query": search_query,
        "date_filter": date_filter,
        "time_filter": time_filter,
        "type_filter": type_filter,
        "only_available": only_available,
        "sort_order": sort_order,
        "type_choices": type_choices,
    })


@login_required
def register_training(request, training_id):
    training = get_object_or_404(Training, id=training_id)

    if not _has_active_membership(request.user):
        messages.error(
            request,
            "Neturite aktyvaus abonemento. Įsigykite abonementą ir bandykite dar kartą."
        )
        return redirect("/trainings/")

    booked = Reservation.objects.filter(training=training, status="BOOKED").count()
    if booked >= training.capacity:
        return redirect("/trainings/")

    Reservation.objects.get_or_create(training=training, user=request.user, defaults={"status": "BOOKED"})

    messages.success(request, "Sėkmingai užsiregistravote į treniruotę!")
    return redirect("/my-reservations/")


@login_required
def my_reservations(request):
    reservations = Reservation.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "gym/my_reservations.html", {"reservations": reservations})


@login_required
def cancel_reservation(request, reservation_id):
    r = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    r.status = "CANCELLED"
    r.save()
    messages.info(request, "Rezervacija atšaukta.")
    return redirect("/my-reservations/")


@login_required
def trainer_trainings(request):
    profile, _ = Profile.objects.get_or_create(user=request.user, defaults={"role": "CLIENT"})
    if profile.role != "TRAINER":
        return redirect("/dashboard/")

    # Bazinis queryset
    trainings = Training.objects.filter(trainer=request.user)

    # --- FILTRAI ---
    # Paieška pagal pavadinimą
    search_query = request.GET.get("q", "").strip()
    if search_query:
        trainings = trainings.filter(title__icontains=search_query)

    # Statusas: SCHEDULED / CANCELLED / "" (visi)
    status_filter = request.GET.get("status", "").strip()
    if status_filter in ("SCHEDULED", "CANCELLED"):
        trainings = trainings.filter(status=status_filter)

    # Laikotarpis: upcoming (būsimos) / past (praeities) / "" (visos)
    period_filter = request.GET.get("period", "").strip()
    now = timezone.now()
    if period_filter == "upcoming":
        trainings = trainings.filter(starts_at__gte=now)
    elif period_filter == "past":
        trainings = trainings.filter(starts_at__lt=now)

    # Rikiavimas: asc (seniausi pirma) / desc (naujausi pirma)
    sort_order = request.GET.get("sort", "asc").strip()
    if sort_order == "desc":
        trainings = trainings.order_by("-starts_at")
    else:
        trainings = trainings.order_by("starts_at")
        sort_order = "asc"  # normalizuojam

    return render(request, "gym/trainer_trainings.html", {
        "trainings": trainings,
        "search_query": search_query,
        "status_filter": status_filter,
        "period_filter": period_filter,
        "sort_order": sort_order,
    })


@login_required
def trainer_calendar(request):
    """Trenerio kalendoriaus puslapis – FullCalendar render."""
    profile, _ = Profile.objects.get_or_create(user=request.user, defaults={"role": "CLIENT"})
    if profile.role != "TRAINER":
        return redirect("/dashboard/")
    return render(request, "gym/trainer_calendar.html", {})


@login_required
def trainer_calendar_events(request):
    """JSON API – FullCalendar kviečia šitą, kad gautų event'us pasirinktam intervalui."""
    from django.http import JsonResponse

    profile, _ = Profile.objects.get_or_create(user=request.user, defaults={"role": "CLIENT"})
    if profile.role != "TRAINER":
        return JsonResponse([], safe=False)

    start = request.GET.get("start")
    end = request.GET.get("end")

    qs = Training.objects.filter(trainer=request.user).annotate(
        booked_count=Count("reservations", filter=Q(reservations__status="BOOKED"))
    )
    if start:
        qs = qs.filter(starts_at__gte=start)
    if end:
        qs = qs.filter(starts_at__lt=end)

    events = []
    for t in qs:
        ends_at = t.starts_at + timedelta(minutes=t.duration_minutes)
        if t.status == "CANCELLED":
            color = "#ef4444"   # raudona
        elif t.booked_count >= t.capacity:
            color = "#f59e0b"   # geltona/oranžinė – pilna
        elif t.booked_count >= t.capacity * 0.5:
            color = "#22c55e"   # žalia – pusiau pilna
        else:
            color = "#4361ee"   # mėlyna – laisvai vietos

        events.append({
            "id": t.id,
            "title": f"{t.title} ({t.booked_count}/{t.capacity})",
            "start": t.starts_at.isoformat(),
            "end": ends_at.isoformat(),
            "url": f"/trainer/trainings/{t.id}/attendees/",
            "backgroundColor": color,
            "borderColor": color,
            "extendedProps": {
                "booked": t.booked_count,
                "capacity": t.capacity,
                "status": t.status,
                "duration": t.duration_minutes,
            },
        })

    return JsonResponse(events, safe=False)


@login_required
def training_attendees(request, training_id):
    profile, _ = Profile.objects.get_or_create(user=request.user, defaults={"role": "CLIENT"})
    if profile.role != "TRAINER":
        return redirect("/dashboard/")

    training = get_object_or_404(Training, id=training_id, trainer=request.user)
    reservations = Reservation.objects.filter(training=training).select_related("user")
    return render(request, "gym/training_attendees.html", {
        "training": training,
        "reservations": reservations,
    })


@login_required
def set_attendance(request, reservation_id, status):
    profile, _ = Profile.objects.get_or_create(user=request.user, defaults={"role": "CLIENT"})
    if profile.role != "TRAINER":
        return redirect("/dashboard/")

    r = get_object_or_404(Reservation, id=reservation_id)

    if r.training.trainer != request.user:
        return redirect("/dashboard/")

    if status in ["ATTENDED", "NO_SHOW"]:
        r.status = status
        r.save()
        messages.success(request, "Statusas atnaujintas.")

    return redirect(f"/trainer/trainings/{r.training.id}/attendees/")


@login_required
def trainer_create_training(request):
    # tik treneriui
    if not hasattr(request.user, "profile") or request.user.profile.role != "TRAINER":
        return HttpResponseForbidden("Neturite teisių")

    if request.method == "POST":
        form = TrainingForm(request.POST, request.FILES)
        if form.is_valid():
            training = form.save(commit=False)
            training.trainer = request.user
            training.save()
            return redirect("/trainer/trainings/")
    else:
        form = TrainingForm()

    # Paveikslėlių galerija – kiekvienam treniruotės tipui priskirta nuotrauka.
    # "key" turi sutapti su forms.py TRAINING_TYPE_CHOICES reikšmėmis,
    # kad JS galėtų automatiškai parinkti nuotrauką pagal pasirinktą tipą.
    gallery_images = [
        {"key": "Joga",            "label": "Joga",       "url": "https://images.unsplash.com/photo-1545205597-3d9d02c29597?w=800&q=80"},
        {"key": "CrossFit",        "label": "CrossFit",   "url": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=800&q=80"},
        {"key": "Spin / Dviratis", "label": "Spin",       "url": "https://images.unsplash.com/photo-1518310383802-640c2de311b2?w=800&q=80"},
        {"key": "Boksas",          "label": "Boksas",     "url": "https://images.unsplash.com/photo-1599058917212-d750089bc07e?w=800&q=80"},
        {"key": "Svorių salė",     "label": "Svoriai",    "url": "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=800&q=80"},
        {"key": "Pilatesas",       "label": "Pilatesas",  "url": "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=800&q=80"},
        {"key": "Zumba",           "label": "Zumba",      "url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&q=80"},
        {"key": "HIIT",            "label": "HIIT",       "url": "https://images.unsplash.com/photo-1549060279-7e168fcee0c2?w=800&q=80"},
        {"key": "Bėgimas",         "label": "Bėgimas",    "url": "https://images.unsplash.com/photo-1552674605-db6ffd4facb5?w=800&q=80"},
        {"key": "Plaukimas",       "label": "Plaukimas",  "url": "https://images.unsplash.com/photo-1530549387789-4c1017266635?w=800&q=80"},
        {"key": "Stretching",      "label": "Stretching", "url": "https://images.unsplash.com/photo-1552693673-1bf958298935?w=800&q=80"},
        {"key": "Kita",            "label": "Kita",       "url": "https://images.unsplash.com/photo-1540497077202-7c8a3999166f?w=800&q=80"},
    ]

    return render(request, "gym/trainer_create_training.html", {
        "form": form,
        "gallery_images": gallery_images,
    })


@login_required
def trainer_cancel_training(request, training_id):
    if not hasattr(request.user, "profile") or request.user.profile.role != "TRAINER":
        return redirect("/dashboard/")

    training = get_object_or_404(Training, id=training_id, trainer=request.user)

    if request.method == "POST":
        note = request.POST.get("note", "").strip()
        training.status = "CANCELLED"
        training.cancellation_note = note
        training.save()
        return redirect("/trainer/trainings/")

    return render(request, "gym/trainer_cancel_training.html", {"training": training})


# ============================================================
# ABONEMENTO PIRKIMAS IR STRIPE MOKĖJIMAS
# ============================================================

@login_required
def membership_buy_page(request):
    plans = MembershipPlan.objects.all().order_by("price")
    return render(request, "gym/membership_buy.html", {"plans": plans})


@login_required
def membership_buy_checkout(request, plan_id):
    plan = get_object_or_404(MembershipPlan, id=plan_id)

    if request.method == "POST":
        form = MembershipPurchaseForm(request.POST)
        if form.is_valid():
            purchase = MembershipPurchase.objects.create(
                user=request.user,
                plan=plan,
                full_name=form.cleaned_data["full_name"],
                phone=form.cleaned_data.get("phone", ""),
                status="PENDING",
            )
            return redirect("membership_stripe_checkout", purchase_id=purchase.id)
    else:
        form = MembershipPurchaseForm()

    return render(request, "gym/membership_checkout.html", {"plan": plan, "form": form})


@login_required
def membership_stripe_checkout(request, purchase_id):
    purchase = get_object_or_404(
        MembershipPurchase, id=purchase_id, user=request.user, status="PENDING"
    )
    plan = purchase.plan

    success_url = request.build_absolute_uri(
        reverse("membership_payment_success", args=[purchase.id])
    ) + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = request.build_absolute_uri(
        reverse("membership_payment_cancel", args=[purchase.id])
    )

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": f"Abonementas: {plan.name}",
                    "description": f"{plan.duration_days} dienų galiojimas",
                },
                "unit_amount": int(plan.price * 100),
            },
            "quantity": 1,
        }],
        customer_email=request.user.email or None,
        metadata={
            "purchase_id": str(purchase.id),
            "user_id": str(request.user.id),
            "plan_id": str(plan.id),
        },
        success_url=success_url,
        cancel_url=cancel_url,
    )

    purchase.stripe_session_id = session.id
    purchase.save(update_fields=["stripe_session_id"])

    return redirect(session.url, permanent=False)


@login_required
def membership_payment_success(request, purchase_id):
    purchase = get_object_or_404(MembershipPurchase, id=purchase_id, user=request.user)

    session_id = request.GET.get("session_id", "")
    if session_id and session_id != purchase.stripe_session_id:
        messages.error(request, "Nepavyko patvirtinti mokėjimo.")
        return redirect("/membership/buy/")

    if purchase.status == "PAID":
        messages.success(request, "Abonementas sėkmingai aktyvuotas!")
        return redirect("/dashboard/")

    try:
        session = stripe.checkout.Session.retrieve(purchase.stripe_session_id)
    except Exception:
        messages.error(request, "Nepavyko susisiekti su mokėjimo sistema.")
        return redirect("/membership/buy/")

    if session.payment_status == "paid":
        purchase.status = "PAID"
        purchase.paid_at = timezone.now()
        purchase.stripe_payment_intent = session.payment_intent or ""
        purchase.save(update_fields=["status", "paid_at", "stripe_payment_intent"])

        _activate_membership_from_purchase(purchase)
        messages.success(request, "Abonementas sėkmingai aktyvuotas!")
        return redirect("/dashboard/")

    messages.info(request, "Laukiama apmokėjimo patvirtinimo…")
    return redirect("/dashboard/")


@login_required
def membership_payment_cancel(request, purchase_id):
    purchase = get_object_or_404(MembershipPurchase, id=purchase_id, user=request.user)
    if purchase.status == "PENDING":
        purchase.status = "REJECTED"
        purchase.save(update_fields=["status"])

    messages.warning(request, "Mokėjimas atšauktas. Galite bandyti dar kartą.")
    return redirect("/membership/buy/")


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            import json
            event = json.loads(payload)
    except Exception:
        return HttpResponse(status=400)

    event_type = event["type"] if isinstance(event, dict) else event.type
    data_object = event["data"]["object"] if isinstance(event, dict) else event.data.object

    if event_type == "checkout.session.completed":
        session_id = data_object["id"] if isinstance(data_object, dict) else data_object.id
        payment_intent = (
            data_object.get("payment_intent", "") if isinstance(data_object, dict)
            else (data_object.payment_intent or "")
        )

        try:
            purchase = MembershipPurchase.objects.get(stripe_session_id=session_id)
        except MembershipPurchase.DoesNotExist:
            return HttpResponse(status=200)

        if purchase.status != "PAID":
            purchase.status = "PAID"
            purchase.paid_at = timezone.now()
            purchase.stripe_payment_intent = payment_intent or ""
            purchase.save(update_fields=["status", "paid_at", "stripe_payment_intent"])
            _activate_membership_from_purchase(purchase)

    return HttpResponse(status=200)
