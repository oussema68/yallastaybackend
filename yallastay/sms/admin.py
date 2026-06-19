from django.contrib import admin

from .models import SmsMessage, SmsTemplate


@admin.register(SmsTemplate)
class SmsTemplateAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("key", "name", "body")
    ordering = ("key",)


@admin.register(SmsMessage)
class SmsMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "to_number",
        "status",
        "template_key",
        "provider_message_id",
        "retry_count",
        "created_at",
    )
    list_filter = ("status", "template_key")
    search_fields = ("to_number", "provider_message_id", "body")
    readonly_fields = ("created_at", "updated_at")
