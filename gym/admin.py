"""Sporto klubo veiklos administracinė sąsaja."""
from django.contrib import admin
from .models import (
    MembershipPlan, Membership, MembershipPurchase,
    Training, Reservation
)


@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_days", "visit_limit", "price")
    search_fields = ("name",)
    list_filter = ("duration_days",)
    ordering = ("price",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "start_date", "end_date", "status", "visits_left")
    list_filter = ("status", "plan")
    search_fields = ("user__username", "user__email")
    date_hierarchy = "start_date"
    ordering = ("-created_at",)


@admin.register(MembershipPurchase)
class MembershipPurchaseAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "created_at", "paid_at")
    list_filter = ("status",)
    search_fields = ("user__username", "user__email", "full_name")
    readonly_fields = ("stripe_session_id", "stripe_payment_intent", "paid_at", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = ("title", "trainer", "starts_at", "duration_minutes", "capacity", "status")
    list_filter = ("status", "trainer")
    search_fields = ("title", "trainer__username")
    date_hierarchy = "starts_at"
    ordering = ("-starts_at",)
    readonly_fields = ("created_at",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("user", "training", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("user__username", "training__title")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    autocomplete_fields = ("user", "training")
