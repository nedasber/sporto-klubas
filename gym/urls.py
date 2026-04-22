from django.urls import path
from . import views

urlpatterns = [
    path("trainings/", views.trainings_list, name="trainings"),
    path("trainings/<int:training_id>/register/", views.register_training, name="register_training"),
    path("my-reservations/", views.my_reservations, name="my_reservations"),

    # Abonementų pirkimas
    path("membership/buy/", views.membership_buy_page, name="membership_buy"),
    path("membership/buy/<int:plan_id>/", views.membership_buy_checkout, name="membership_buy_checkout"),

    # Stripe mokėjimai
    path("membership/pay/<int:purchase_id>/", views.membership_stripe_checkout, name="membership_stripe_checkout"),
    path("membership/pay/<int:purchase_id>/success/", views.membership_payment_success, name="membership_payment_success"),
    path("membership/pay/<int:purchase_id>/cancel/", views.membership_payment_cancel, name="membership_payment_cancel"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
]