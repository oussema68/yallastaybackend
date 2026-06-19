from rest_framework import serializers
from django.contrib.auth import get_user_model

from core.text_sanitize import sanitize_plain_text

from .models import Conversation, Message
from .team_user import is_yallastay_team_user
from .validators import validate_message_attachment
from listings.models import Listing
from listings.serializers import ListingListSerializer

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source="sender.email", read_only=True)
    sender_first_name = serializers.SerializerMethodField()
    sender_is_yallastay_team = serializers.SerializerMethodField()
    has_attachment = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "sender",
            "sender_email",
            "sender_first_name",
            "sender_is_yallastay_team",
            "content",
            "has_attachment",
            "attachment_name",
            "attachment_url",
            "read_at",
            "created_at",
        ]
        read_only_fields = ["sender", "read_at", "created_at"]

    def get_sender_first_name(self, obj):
        if is_yallastay_team_user(obj.sender):
            return "Yallastay Team"
        return (obj.sender.first_name or "").strip() or "User"

    def get_sender_is_yallastay_team(self, obj):
        return is_yallastay_team_user(obj.sender)

    def get_has_attachment(self, obj):
        return bool(obj.attachment)

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None
        request = self.context.get("request")
        url = obj.attachment.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class ConversationSerializer(serializers.ModelSerializer):
    """Conversation with listing context and the other participant."""

    listing_title = serializers.CharField(source="listing.title", read_only=True)
    listing_detail = ListingListSerializer(source="listing", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    other_user = serializers.SerializerMethodField()
    participants_emails = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "kind",
            "kind_display",
            "listing",
            "listing_title",
            "listing_detail",
            "other_user",
            "participants",
            "participants_emails",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]

    def get_other_user(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        for u in obj.participants.all():
            if u.pk != request.user.pk:
                first = (getattr(u, "first_name", None) or "").strip()
                role = None
                try:
                    role = u.profile.role
                except Exception:
                    pass
                return {
                    "id": u.pk,
                    "first_name": first or "User",
                    "role": role,
                }
        return None

    def get_participants_emails(self, obj):
        return [u.email for u in obj.participants.all()]

    def _last_message_preview(self, last: Message) -> str:
        text = (last.content or "").strip()
        if last.attachment:
            label = (last.attachment_name or "File").strip() or "File"
            if text:
                return f"{text} [file: {label}]"
            return f"Attachment: {label}"
        return text[:100]

    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        if last:
            preview = self._last_message_preview(last)
            return {
                "id": last.id,
                "content": preview[:100],
                "created_at": last.created_at,
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        return (
            obj.messages.exclude(sender=request.user)
            .filter(read_at__isnull=True)
            .count()
        )


class ConversationCreateSerializer(serializers.Serializer):
    """Start renter inquiry conversation on a listing."""

    listing_id = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.filter(status="active")
    )


class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(
        max_length=20000, required=False, allow_blank=True, default=""
    )
    attachment = serializers.FileField(required=False, allow_null=True)

    def validate_content(self, value):
        return sanitize_plain_text(value or "")

    def validate_attachment(self, value):
        return validate_message_attachment(value)

    def validate(self, data):
        content = (data.get("content") or "").strip()
        attachment = data.get("attachment")
        if not content and not attachment:
            raise serializers.ValidationError("Enter a message or attach a file.")
        data["content"] = content
        return data
