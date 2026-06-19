from django.contrib import admin
from .models import RoommateProfile, RoommateInterest


@admin.register(RoommateProfile)
class RoommateProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_looking", "move_in_date", "created_at")
    list_filter = ("is_looking",)
    filter_horizontal = ["preferred_areas"]


@admin.register(RoommateInterest)
class RoommateInterestAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "status", "created_at")
    list_filter = ("status",)
