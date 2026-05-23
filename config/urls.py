from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from gym import views as gym_views
from accounts.forms import LoginForm

urlpatterns = [
    path("", RedirectView.as_view(url="/login/", permanent=False)),

    # Django integruotas admin (paliktas backup'ui)
    path("django-admin/", admin.site.urls),
    # Mūsų administracinė panelė
    path("manage/", include("manage_panel.urls")),

    # Auth
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=LoginForm,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Dashboard
    path("dashboard/", gym_views.dashboard, name="dashboard"),

    # Gamification
    path("leaderboard/", gym_views.leaderboard, name="leaderboard"),
    path("achievements/", gym_views.achievements_page, name="achievements_page"),

    # Pranešimai
    path("notifications/mark-seen/", gym_views.mark_notifications_seen, name="mark_notifications_seen"),

    # Client
    path("trainings/", gym_views.trainings_list, name="trainings_list"),
    path("trainings/<int:training_id>/register/", gym_views.register_training, name="register_training"),
    path("my-reservations/", gym_views.my_reservations, name="my_reservations"),
    path("my-reservations/<int:reservation_id>/cancel/", gym_views.cancel_reservation, name="cancel_reservation"),

    # Trainer
    path("trainer/trainings/", gym_views.trainer_trainings, name="trainer_trainings"),
    path("trainer/trainings/create/", gym_views.trainer_create_training, name="trainer_create_training"),
    path("trainer/trainings/<int:training_id>/edit/", gym_views.trainer_edit_training, name="trainer_edit_training"),
    path("trainer/trainings/<int:training_id>/attendees/", gym_views.training_attendees, name="training_attendees"),
    path("trainer/trainings/<int:training_id>/cancel/", gym_views.trainer_cancel_training, name="trainer_cancel_training"),
    path("trainer/reservations/<int:reservation_id>/<str:status>/", gym_views.set_attendance, name="set_attendance"),
    path("trainer/calendar/", gym_views.trainer_calendar, name="trainer_calendar"),
    path("trainer/calendar/events/", gym_views.trainer_calendar_events, name="trainer_calendar_events"),

    # Membership
    path("membership/buy/", gym_views.membership_buy_page, name="membership_buy_page"),
    path("membership/buy/<int:plan_id>/", gym_views.membership_buy_checkout, name="membership_buy_checkout"),

    # Stripe mokėjimai
    path("membership/pay/<int:purchase_id>/", gym_views.membership_stripe_checkout, name="membership_stripe_checkout"),
    path("membership/pay/<int:purchase_id>/success/", gym_views.membership_payment_success, name="membership_payment_success"),
    path("membership/pay/<int:purchase_id>/cancel/", gym_views.membership_payment_cancel, name="membership_payment_cancel"),
    path("stripe/webhook/", gym_views.stripe_webhook, name="stripe_webhook"),

    # Accounts app
    path("", include("accounts.urls")),

    # Kalbos perjungimas
    path("i18n/", include("django.conf.urls.i18n")),
]

# Media failai development režime
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
