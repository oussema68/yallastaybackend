from django.contrib import admin

from .models import EmailMessage, EmailTemplate


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("key", "name", "subject")
    ordering = ("key",)


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "to_email",
        "subject",
        "status",
        "template_key",
        "provider_message_id",
        "created_at",
    )
    list_filter = ("status", "template_key")
    search_fields = ("to_email", "subject", "provider_message_id")
    readonly_fields = ("created_at", "updated_at")
