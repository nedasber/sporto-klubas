from django.urls import path
from . import views

urlpatterns = [
    path("trainings/", views.trainings_list, name="trainings"),
    path("trainings/<int:training_id>/register/", views.register_training, name="register_training"),
    path("my-reservations/", views.my_reservations, name="my_reservations"),
    path("membership/buy/", views.membership_buy_page),
    path("membership/buy/<int:plan_id>/", views.membership_buy_checkout),
]
