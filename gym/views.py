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

    return Membership.objects.create(
        user=purchase.user,
        plan=plan,
        start_date=start,
        end_date=end,
        status="ACTIVE",
        visits_left=visits_left,
    )


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

    # --- MOTYVACINĖ SISTEMA ---
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
    }

    return render(request, "gym/dashboard.html", {
        "role": profile.role,                # gali naudoti šablone vietoj request.user.profile.role
        "membership_info": membership_info,  # tavo dashboard.html jau naudoja šitą
        "stats": stats,                      # tavo dashboard.html jau naudoja šitą
        "upcoming": upcoming,                # tavo dashboard.html jau naudoja šitą
        "gamification_info": gamification_info,  # motyvacinė sistema
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

    # Paveikslėlių galerija (Unsplash – nemokami, komerciškai leidžiami)
    gallery_images = [
        {"label": "Joga", "url": "https://images.unsplash.com/photo-1545205597-3d9d02c29597?w=800&q=80"},
        {"label": "CrossFit", "url": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=800&q=80"},
        {"label": "Spin", "url": "https://images.unsplash.com/photo-1518310383802-640c2de311b2?w=800&q=80"},
        {"label": "Boksas", "url": "https://images.unsplash.com/photo-1599058917212-d750089bc07e?w=800&q=80"},
        {"label": "Svoriai", "url": "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=800&q=80"},
        {"label": "Pilatesas", "url": "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=800&q=80"},
        {"label": "Zumba", "url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&q=80"},
        {"label": "HIIT", "url": "https://images.unsplash.com/photo-1549060279-7e168fcee0c2?w=800&q=80"},
        {"label": "Bėgimas", "url": "https://images.unsplash.com/photo-1552674605-db6ffd4facb5?w=800&q=80"},
        {"label": "Plaukimas", "url": "https://images.unsplash.com/photo-1530549387789-4c1017266635?w=800&q=80"},
        {"label": "Stretching", "url": "https://images.unsplash.com/photo-1552693673-1bf958298935?w=800&q=80"},
        {"label": "Funkcinė", "url": "https://images.unsplash.com/photo-1540497077202-7c8a3999166f?w=800&q=80"},
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
    """
    Kliento duomenų (vardo, telefono) rinkimas prieš mokėjimą.
    Po formos patvirtinimo – sukuriamas MembershipPurchase (PENDING)
    ir klientas nukreipiamas į Stripe Checkout sesiją.
    """
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
    """Sukuria Stripe Checkout sesiją ir nukreipia klientą į Stripe mokėjimo puslapį."""
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
                "unit_amount": int(plan.price * 100),  # centais
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
    """
    Kliento grįžimas po sėkmingo apmokėjimo.
    Tikriname Stripe sesijos būseną – jei paid, aktyvuojame narystę.
    """
    purchase = get_object_or_404(MembershipPurchase, id=purchase_id, user=request.user)

    session_id = request.GET.get("session_id", "")
    if session_id and session_id != purchase.stripe_session_id:
        messages.error(request, "Nepavyko patvirtinti mokėjimo.")
        return redirect("/membership/buy/")

    # Jei webhook'as jau suveikė – narystė jau aktyvi, tiesiog rodom dashboard
    if purchase.status == "PAID":
        messages.success(request, "Abonementas sėkmingai aktyvuotas!")
        return redirect("/dashboard/")

    # Papildomas saugiklis: patikrinam tiesiai per Stripe API
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
    """Kliento grįžimas, kai mokėjimas buvo atšauktas."""
    purchase = get_object_or_404(MembershipPurchase, id=purchase_id, user=request.user)
    if purchase.status == "PENDING":
        purchase.status = "REJECTED"
        purchase.save(update_fields=["status"])

    messages.warning(request, "Mokėjimas atšauktas. Galite bandyti dar kartą.")
    return redirect("/membership/buy/")


@csrf_exempt
def stripe_webhook(request):
    """
    Stripe webhook'as – automatiškai aktyvuoja narystę po sėkmingo mokėjimo.
    Veikia patikimiau nei success_url, nes Stripe siunčia užklausą net jei
    klientas uždaro naršyklę po mokėjimo.
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            # Be webhook secret – naudojame įvykį be parašo patikros (tik testavimui)
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