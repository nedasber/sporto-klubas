from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Profile
from .forms import MembershipPurchaseForm, TrainingForm
from .models import Membership, MembershipPlan, Reservation, Training


def _has_active_membership(user) -> bool:
    today = timezone.now().date()
    return Membership.objects.filter(
        user=user,
        status="ACTIVE",
        start_date__lte=today,
        end_date__gte=today,
    ).exists()


@login_required
def dashboard(request):
    # Užtikrinam, kad profilis egzistuoja (kad nedaužtų DoesNotExist)
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"role": "CLIENT"},  # jei pas tave kita default reikšmė – pakeisk
    )

    today = timezone.now().date()

    # Aktyvi narystė
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

        visit_limit = membership.plan.visit_limit  # None jei neribota
        visits_left = membership.visits_left

        visit_progress = 0
        if visit_limit:
            # jei dėl kokių nors priežasčių visits_left None – laikom kad pilnas limitas
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

    # Statistika
    stats = {
        "booked": Reservation.objects.filter(user=request.user, status="BOOKED").count(),
        "cancelled": Reservation.objects.filter(user=request.user, status="CANCELLED").count(),
        "attended": Reservation.objects.filter(user=request.user, status="ATTENDED").count(),
        "no_show": Reservation.objects.filter(user=request.user, status="NO_SHOW").count(),
    }

    # Artimiausios treniruotės (rezervacijos)
    upcoming = (
        Reservation.objects.filter(
            user=request.user,
            status="BOOKED",
            training__starts_at__gte=timezone.now(),
        )
        .select_related("training", "training__trainer")
        .order_by("training__starts_at")[:5]
    )

    return render(request, "gym/dashboard.html", {
        "role": profile.role,                # gali naudoti šablone vietoj request.user.profile.role
        "membership_info": membership_info,  # tavo dashboard.html jau naudoja šitą
        "stats": stats,                      # tavo dashboard.html jau naudoja šitą
        "upcoming": upcoming,                # tavo dashboard.html jau naudoja šitą
    })


def trainings_list(request):
    trainings_qs = (
        Training.objects.filter(starts_at__gte=timezone.now())
        .annotate(
            booked_count=Count("reservations", filter=Q(reservations__status="BOOKED"))
        )
        .order_by("starts_at")
    )

    trainings = []
    for t in trainings_qs:
        t.left_count = max(t.capacity - t.booked_count, 0)
        t.is_full = (t.left_count <= 0)
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

    return render(request, "gym/trainings_list.html", {
        "trainings": trainings,
        "my_booked_ids": my_booked_ids,
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

    trainings = Training.objects.filter(trainer=request.user).order_by("starts_at")
    return render(request, "gym/trainer_trainings.html", {"trainings": trainings})


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

    # Treneris gali keisti tik savo treniruotėms
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
        form = TrainingForm(request.POST)
        if form.is_valid():
            training = form.save(commit=False)
            training.trainer = request.user
            training.save()
            return redirect("/trainer/trainings/")
    else:
        form = TrainingForm()

    return render(request, "gym/trainer_create_training.html", {"form": form})


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
            # jei nori – čia galima sukurti MembershipPurchase, bet dabar tiesiog kuriam narystę
            _full_name = form.cleaned_data.get("full_name")
            _phone = form.cleaned_data.get("phone")

            start = timezone.now().date()
            end = start + timedelta(days=plan.duration_days)

            visits_left = plan.visit_limit if plan.visit_limit else None

            Membership.objects.create(
                user=request.user,
                plan=plan,
                start_date=start,
                end_date=end,
                status="ACTIVE",
                visits_left=visits_left,
            )

            messages.success(request, "Abonementas aktyvuotas!")
            return redirect("/dashboard/")
    else:
        form = MembershipPurchaseForm()

    return render(request, "gym/membership_checkout.html", {"plan": plan, "form": form})
