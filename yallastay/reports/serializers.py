from rest_framework import serializers
from django.contrib.auth import get_user_model

from core.text_sanitize import sanitize_plain_text

from .models import Report
from listings.models import Listing

User = get_user_model()


class ReportSerializer(serializers.ModelSerializer):
    reporter_email = serializers.EmailField(source="reporter.email", read_only=True)
    reported_listing_title = serializers.CharField(
        source="reported_listing.title", read_only=True, allow_null=True
    )
    reported_user_email = serializers.EmailField(
        source="reported_user.email", read_only=True, allow_null=True
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "reporter",
            "reporter_email",
            "reported_listing",
            "reported_listing_title",
            "reported_user",
            "reported_user_email",
            "reason",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["reporter", "status", "created_at", "updated_at"]


class ReportCreateSerializer(serializers.Serializer):
    """Submit a report. Must provide either listing_id or user_id."""

    listing_id = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.all(), required=False, allow_null=True
    )
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    reason = serializers.CharField(max_length=10000)

    def validate_reason(self, value):
        return sanitize_plain_text(value or "")

    def validate(self, attrs):
        if not attrs.get("listing_id") and not attrs.get("user_id"):
            raise serializers.ValidationError(
                "Provide either listing_id or user_id to report."
            )
        if attrs.get("listing_id") and attrs.get("user_id"):
            raise serializers.ValidationError(
                "Report either a listing or a user, not both."
            )
        return attrs
