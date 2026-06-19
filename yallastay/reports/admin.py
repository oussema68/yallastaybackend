from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "reporter",
        "reported_listing",
        "reported_user",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("reporter__email", "reason")
    readonly_fields = (
        "reporter",
        "reported_listing",
        "reported_user",
        "reason",
        "created_at",
    )
    fieldsets = (
        (None, {"fields": ("reporter", "reported_listing", "reported_user", "reason")}),
        ("Moderation", {"fields": ("status", "admin_notes", "updated_at")}),
    )
