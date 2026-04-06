from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from gym import views as gym_views

urlpatterns = [
    path("", RedirectView.as_view(url="/login/", permanent=False)),

    path("admin/", admin.site.urls),

    # Auth
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Dashboard
    path("dashboard/", gym_views.dashboard, name="dashboard"),

    # Client
    path("trainings/", gym_views.trainings_list, name="trainings_list"),
    path("trainings/<int:training_id>/register/", gym_views.register_training, name="register_training"),
    path("my-reservations/", gym_views.my_reservations, name="my_reservations"),
    path("my-reservations/<int:reservation_id>/cancel/", gym_views.cancel_reservation, name="cancel_reservation"),

    # Trainer
    path("trainer/trainings/", gym_views.trainer_trainings, name="trainer_trainings"),
    path("trainer/trainings/create/", gym_views.trainer_create_training, name="trainer_create_training"),
    path("trainer/trainings/<int:training_id>/attendees/", gym_views.training_attendees, name="training_attendees"),
    path("trainer/trainings/<int:training_id>/cancel/", gym_views.trainer_cancel_training, name="trainer_cancel_training"),
    path("trainer/reservations/<int:reservation_id>/<str:status>/", gym_views.set_attendance, name="set_attendance"),

    # Membership
    path("membership/buy/", gym_views.membership_buy_page, name="membership_buy_page"),
    path("membership/buy/<int:plan_id>/", gym_views.membership_buy_checkout, name="membership_buy_checkout"),

    # Accounts app
    path("", include("accounts.urls")),
]