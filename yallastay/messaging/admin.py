from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.StackedInline):
    model = Message
    extra = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("listing", "created_at")
    filter_horizontal = ["participants"]
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "conversation",
        "sender",
        "content_preview",
        "read_at",
        "created_at",
    )
    list_filter = ("read_at",)

    def content_preview(self, obj):
        return (obj.content[:50] + "...") if len(obj.content) > 50 else obj.content

    content_preview.short_description = "Content"
