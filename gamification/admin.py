from django.contrib import admin
from .models import UserProgress, Achievement, UserAchievement


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "points", "level", "updated_at")
    list_filter = ("level",)
    search_fields = ("user__username",)
    ordering = ("-points",)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "points_reward", "icon")
    search_fields = ("code", "name")


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement", "earned_at")
    list_filter = ("achievement",)
    search_fields = ("user__username", "achievement__name")
    ordering = ("-earned_at",)
