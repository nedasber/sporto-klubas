from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

from .forms import RegisterForm
from .models import Profile
from .emails import send_verification_email

User = get_user_model()


def register_view(request):
    if request.user.is_authenticated:
        return redirect("/dashboard/")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            # NEAKTYVUOJAM, kol nepatvirtino el. pašto
            user.is_active = False
            user.save()

            profile, _ = Profile.objects.get_or_create(user=user, defaults={"role": "CLIENT"})
            profile.email_verified = False
            profile.save()

            # Siunčiam patvirtinimo laišką
            try:
                send_verification_email(user, request=request)
                messages.success(
                    request,
                    "Registracija sėkminga! Į jūsų el. paštą išsiuntėme patvirtinimo nuorodą. "
                    "Patvirtinkite paskyrą, kad galėtumėte prisijungti."
                )
            except Exception as exc:
                messages.warning(
                    request,
                    f"Paskyra sukurta, bet nepavyko išsiųsti patvirtinimo laiško. "
                    f"Susisiekite su administratoriumi. ({exc})"
                )

            return redirect("/login/?registered=1")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def verify_email_view(request, token):
    """Patvirtina vartotojo el. paštą pagal token'ą."""
    try:
        profile = Profile.objects.select_related("user").get(verification_token=token)
    except Profile.DoesNotExist:
        return render(request, "accounts/verify_result.html", {
            "ok": False,
            "title": "Nuoroda neteisinga arba jau panaudota",
            "message": "Patvirtinimo nuoroda nerasta. Galbūt ji buvo panaudota anksčiau, "
                       "arba jūsų paskyra jau patvirtinta. Pabandykite prisijungti.",
        })

    user = profile.user

    if profile.email_verified:
        return render(request, "accounts/verify_result.html", {
            "ok": True,
            "title": "Paskyra jau patvirtinta",
            "message": "Jūsų paskyra jau patvirtinta. Galite prisijungti.",
        })

    # Pažymim, kad patvirtinta
    profile.email_verified = True
    profile.verification_token = ""  # Sunaikinam token'ą, kad nebeveiktų pakartotinai
    profile.save(update_fields=["email_verified", "verification_token"])

    user.is_active = True
    user.save(update_fields=["is_active"])

    # Iškart prijungiam
    user.backend = "django.contrib.auth.backends.ModelBackend"
    login(request, user)
    messages.success(request, "El. paštas patvirtintas! Sveiki sugrįžę.")
    return redirect("/dashboard/")


@login_required
def resend_verification_view(request):
    """Iš naujo siunčia patvirtinimo laišką."""
    profile = request.user.profile

    if profile.email_verified:
        messages.info(request, "Jūsų paskyra jau patvirtinta.")
        return redirect("/dashboard/")

    try:
        send_verification_email(request.user, request=request)
        messages.success(request, "Patvirtinimo laiškas išsiųstas iš naujo. Patikrinkite savo el. paštą.")
    except Exception as exc:
        messages.error(request, f"Nepavyko išsiųsti laiško: {exc}")

    return redirect("/dashboard/")
