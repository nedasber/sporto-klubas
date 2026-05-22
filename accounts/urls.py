from django.urls import path
from .views import register_view, verify_email_view, resend_verification_view

urlpatterns = [
    path("register/", register_view, name="register"),
    path("verify-email/<str:token>/", verify_email_view, name="verify_email"),
    path("resend-verification/", resend_verification_view, name="resend_verification"),
]
