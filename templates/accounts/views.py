# accounts/views.py
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import render, redirect
from .forms import RegisterForm
from .models import Profile

def register(request):
    if request.user.is_authenticated:
        return redirect("/dashboard/")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Sukuriam profilį naujam useriui
            Profile.objects.get_or_create(user=user, defaults={"role": "CLIENT"})
            login(request, user)
            messages.success(request, "Registracija sėkminga! Prisijungėte.")
            return redirect("/dashboard/")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})
