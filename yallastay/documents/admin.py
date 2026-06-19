from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("user", "document_type", "content_type", "object_id", "created_at")
    list_filter = ("document_type",)
