"""Motyvacinės sistemos administracinė sąsaja."""
from django.contrib import admin
from .models import UserProgress, Achievement, UserAchievement


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "points", "level", "current_streak", "longest_streak", "last_attendance_date")
    list_filter = ("level",)
    search_fields = ("user__username",)
    ordering = ("-points",)
    readonly_fields = ("updated_at",)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "points_reward", "icon")
    search_fields = ("name", "code", "description")
    ordering = ("points_reward",)


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement", "earned_at")
    list_filter = ("achievement",)
    search_fields = ("user__username", "achievement__name")
    date_hierarchy = "earned_at"
    ordering = ("-earned_at",)
    readonly_fields = ("earned_at",)
