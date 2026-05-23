"""Vartotojų ir Profilių administracinė sąsaja."""
from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import UserAdmin

from accounts.models import Profile, EmailLog


# Globalūs admin parametrai
admin.site.site_header = "Sporto klubas – Administracija"
admin.site.site_title = "Sporto klubas"
admin.site.index_title = "Valdymo skydelis"


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name = "Profilis"
    verbose_name_plural = "Profilio nustatymai"
    fields = ("role", "email_verified", "last_notifications_seen_at")


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ("username", "email", "get_role", "is_active", "is_staff", "date_joined")
    list_filter = ("is_staff", "is_active", "profile__role")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)

    def get_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except Profile.DoesNotExist:
            return "—"
    get_role.short_description = "Rolė"


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Paslepiam Groups (nenaudojam grupių)
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "object_id", "sent_at")
    list_filter = ("kind",)
    search_fields = ("user__username",)
    date_hierarchy = "sent_at"
    ordering = ("-sent_at",)
    readonly_fields = ("user", "kind", "object_id", "sent_at")

    def has_add_permission(self, request):
        return False
