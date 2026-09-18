from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Follow, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Profile", {"fields": ("display_name", "bio", "email_verified")}),)
    list_display = ("username", "email", "display_name", "email_verified", "date_joined")
    list_filter = ("email_verified", "is_staff", "is_active")
    search_fields = ("username", "email", "display_name")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")
    raw_id_fields = ("follower", "following")
