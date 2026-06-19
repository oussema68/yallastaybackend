from rest_framework import serializers
from django.contrib.auth import get_user_model

from core.text_sanitize import sanitize_plain_text

from .models import Review, ReviewResponse
from listings.models import Listing

User = get_user_model()


class ReviewResponseSerializer(serializers.ModelSerializer):
    """Landlord/realtor reply to a review."""

    class Meta:
        model = ReviewResponse
        fields = ["id", "response_text", "created_at"]


class ReviewSerializer(serializers.ModelSerializer):
    """Review with optional response."""

    reviewer_email = serializers.EmailField(source="reviewer.email", read_only=True)
    reviewee_email = serializers.EmailField(source="reviewee.email", read_only=True)
    listing_title = serializers.CharField(
        source="listing.title", read_only=True, allow_null=True
    )
    response = ReviewResponseSerializer(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "reviewer",
            "reviewer_email",
            "reviewee",
            "reviewee_email",
            "listing",
            "listing_title",
            "rating",
            "comment",
            "response",
            "created_at",
        ]
        read_only_fields = ["reviewer", "created_at"]


class ReviewCreateSerializer(serializers.Serializer):
    """Create review. Requires UAE ID verification."""

    reviewee_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    listing_id = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.all(), required=False, allow_null=True
    )
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=5000)

    def validate_comment(self, value):
        return sanitize_plain_text(value or "")

    def validate_reviewee_id(self, value):
        if value == self.context["request"].user:
            raise serializers.ValidationError("You cannot review yourself.")
        return value


class ReviewResponseCreateSerializer(serializers.ModelSerializer):
    """Create landlord reply to a review. Only reviewee can respond."""

    class Meta:
        model = ReviewResponse
        fields = ["response_text"]

    def validate_response_text(self, value):
        return sanitize_plain_text(value or "")
