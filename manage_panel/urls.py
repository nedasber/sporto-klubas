from django.urls import path
from . import views

app_name = "manage_panel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    # Vartotojai
    path("users/", views.users_list, name="users_list"),
    path("users/create/", views.user_create, name="user_create"),
    path("users/<int:user_id>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:user_id>/delete/", views.user_delete, name="user_delete"),

    # Treniruotės
    path("trainings/", views.trainings_list, name="trainings_list"),
    path("trainings/<int:training_id>/delete/", views.training_delete, name="training_delete"),

    # Abonementų planai
    path("plans/", views.plans_list, name="plans_list"),
    path("plans/create/", views.plan_create, name="plan_create"),
    path("plans/<int:plan_id>/edit/", views.plan_edit, name="plan_edit"),
    path("plans/<int:plan_id>/delete/", views.plan_delete, name="plan_delete"),

    # Narystės
    path("memberships/", views.memberships_list, name="memberships_list"),
    path("memberships/<int:membership_id>/<str:new_status>/", views.membership_change_status, name="membership_change_status"),

    # Pirkimai
    path("purchases/", views.purchases_list, name="purchases_list"),

    # Pasiekimai
    path("achievements/", views.achievements_list, name="achievements_list"),
    path("achievements/create/", views.achievement_create, name="achievement_create"),
    path("achievements/<int:achievement_id>/edit/", views.achievement_edit, name="achievement_edit"),
    path("achievements/<int:achievement_id>/delete/", views.achievement_delete, name="achievement_delete"),

    # El. laiškų žurnalas
    path("email-log/", views.email_log, name="email_log"),
]
