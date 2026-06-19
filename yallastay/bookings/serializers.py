from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model

from core.text_sanitize import sanitize_plain_text

from esign.models import LeaseSigningSession

from .move_in_guidance import MOVE_IN_GUIDANCE
from .party import reservation_party
from .models import ViewingRequest, Reservation
from listings.models import Listing

User = get_user_model()


class ListingMinimalSerializer(serializers.ModelSerializer):
    """Minimal listing info for viewing/reservation responses."""

    area_name = serializers.CharField(source="area.name", read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "price",
            "currency",
            "address",
            "area",
            "area_name",
            "leased",
        ]


class ViewingRequestSerializer(serializers.ModelSerializer):
    listing_detail = ListingMinimalSerializer(source="listing", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ViewingRequest
        fields = [
            "id",
            "listing",
            "listing_detail",
            "user",
            "user_email",
            "requested_datetime",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user", "status", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ViewingRequestCreateSerializer(serializers.Serializer):
    """Create viewing request."""

    listing_id = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.filter(status="active")
    )
    requested_datetime = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_notes(self, value):
        return sanitize_plain_text(value or "")


class ViewingRequestUpdateSerializer(serializers.Serializer):
    """Confirm or reject viewing (landlord/realtor only)."""

    status = serializers.ChoiceField(choices=["confirmed", "rejected"])


class ReservationSerializer(serializers.ModelSerializer):
    listing_detail = ListingMinimalSerializer(source="listing", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    lease_status = serializers.SerializerMethodField()
    renter_first_name = serializers.CharField(
        source="user.first_name", read_only=True, default=""
    )
    keys_received = serializers.SerializerMethodField()
    move_in_guidance = serializers.SerializerMethodField()
    platform_feedback = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            "id",
            "listing",
            "listing_detail",
            "user",
            "user_email",
            "renter_first_name",
            "start_date",
            "end_date",
            "status",
            "deposit_amount",
            "currency",
            "notes",
            "external_reference",
            "dld_metadata",
            "lease_status",
            "keys_received",
            "keys_received_at",
            "move_in_guidance",
            "platform_feedback",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "user",
            "status",
            "notes",
            "external_reference",
            "dld_metadata",
            "lease_status",
            "keys_received",
            "keys_received_at",
            "move_in_guidance",
            "platform_feedback",
            "created_at",
            "updated_at",
        ]

    def get_keys_received(self, obj):
        return obj.keys_received_at is not None

    def get_move_in_guidance(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        if reservation_party(request, obj) != "renter":
            return None
        if obj.status not in ("confirmed", "completed"):
            return None
        return MOVE_IN_GUIDANCE

    def get_platform_feedback(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        if reservation_party(request, obj) != "renter":
            return ""
        return obj.platform_feedback or ""

    def get_lease_status(self, obj):
        """none | pending_signatures | fully_signed - drives dashboard UI."""
        try:
            ls = obj.lease_signing
        except LeaseSigningSession.DoesNotExist:
            return "none"
        if ls.status == "completed":
            return "fully_signed"
        return "pending_signatures"


class ReservationCreateSerializer(serializers.Serializer):
    """Create reservation (in-app rental request)."""

    listing_id = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.filter(status="active")
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    deposit_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=0
    )
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate_notes(self, value):
        return sanitize_plain_text(value or "")

    def validate(self, attrs):
        if attrs["start_date"] >= attrs["end_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date must be after start date."}
            )
        today = timezone.now().date()
        days_until_start = (attrs["start_date"] - today).days
        if days_until_start < 2 or days_until_start > 15:
            raise serializers.ValidationError(
                {"start_date": "Lease start must be between 2 and 15 days from today."}
            )
        request = self.context.get("request")
        listing = attrs["listing_id"]
        if request and request.user.is_authenticated:
            if listing.listed_by_id == request.user.id:
                raise serializers.ValidationError(
                    {
                        "listing_id": "You cannot create a rental request on your own listing."
                    }
                )
            try:
                role = request.user.profile.role
            except Exception:
                role = None
            if role not in ("tenant", "student"):
                raise serializers.ValidationError(
                    {
                        "detail": "Only renter accounts (tenant or verified student) can rent from the app."
                    }
                )
        return attrs


class ReservationStatusUpdateSerializer(serializers.Serializer):
    """Lister or renter updates reservation status."""

    status = serializers.ChoiceField(choices=["confirmed", "cancelled", "completed"])


class ReservationMoveInUpdateSerializer(serializers.Serializer):
    """Renter: confirm keys + optional private platform feedback."""

    keys_received = serializers.BooleanField(required=False)
    platform_feedback = serializers.CharField(
        required=False, allow_blank=True, max_length=4000
    )

    def validate_platform_feedback(self, value):
        return sanitize_plain_text(value or "")

    def validate(self, attrs):
        data_keys = (
            set(self.initial_data.keys())
            if isinstance(self.initial_data, dict)
            else set()
        )
        if not data_keys.intersection({"keys_received", "platform_feedback"}):
            raise serializers.ValidationError(
                "Provide at least one of: keys_received, platform_feedback."
            )
        if "keys_received" in attrs and attrs["keys_received"] is False:
            raise serializers.ValidationError(
                {"keys_received": "Only true is accepted to confirm key handover."}
            )
        return attrs
