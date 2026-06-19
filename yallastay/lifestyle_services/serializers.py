from django.utils import timezone
from rest_framework import serializers

from accounts.models import UAEIDVerification
from .models import (
    LifestylePartner,
    LifestylePlan,
    LifestylePlanBenefit,
    LifestylePlanSection,
    LifestyleService,
    LifestyleSubscription,
    LifestyleSubscriptionPreference,
)
from bookings.models import Reservation


class LifestyleServiceSerializer(serializers.ModelSerializer):
    service_type_display = serializers.CharField(
        source="get_service_type_display", read_only=True
    )

    class Meta:
        model = LifestyleService
        fields = ["id", "service_type", "service_type_display", "details"]


class LifestylePlanBenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = LifestylePlanBenefit
        fields = ["id", "text", "sort_order"]


class LifestylePlanSectionSerializer(serializers.ModelSerializer):
    benefits = LifestylePlanBenefitSerializer(many=True, read_only=True)

    class Meta:
        model = LifestylePlanSection
        fields = ["id", "title", "emoji", "sort_order", "benefits"]


class LifestylePlanSerializer(serializers.ModelSerializer):
    services = LifestyleServiceSerializer(many=True, read_only=True)
    sections = LifestylePlanSectionSerializer(many=True, read_only=True)

    class Meta:
        model = LifestylePlan
        fields = [
            "id",
            "name",
            "tier",
            "price",
            "currency",
            "description",
            "tagline",
            "is_most_popular",
            "services",
            "sections",
        ]


class LifestylePartnerSerializer(serializers.ModelSerializer):
    partner_type_display = serializers.CharField(
        source="get_partner_type_display", read_only=True
    )

    class Meta:
        model = LifestylePartner
        fields = [
            "id",
            "partner_type",
            "partner_type_display",
            "name",
            "area_label",
            "sort_order",
        ]


class LifestyleSubscriptionPreferenceSerializer(serializers.ModelSerializer):
    gym_partner = serializers.PrimaryKeyRelatedField(
        queryset=LifestylePartner.objects.filter(partner_type="gym"),
        allow_null=True,
        required=False,
    )
    gym_partner_detail = LifestylePartnerSerializer(
        source="gym_partner", read_only=True
    )

    class Meta:
        model = LifestyleSubscriptionPreference
        fields = [
            "id",
            "gym_partner",
            "gym_partner_detail",
            "cleaning_weekday",
            "cleaning_time_window",
            "notes",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def validate_gym_partner(self, value):
        if value is None:
            return value
        if value.partner_type != "gym":
            raise serializers.ValidationError("Selected partner must be a gym.")
        if not value.is_active:
            raise serializers.ValidationError("This partner is not available.")
        return value


class LifestyleSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    listing_title = serializers.CharField(
        source="reservation.listing.title", read_only=True
    )
    latest_payment = serializers.SerializerMethodField()
    lifestyle_preferences = LifestyleSubscriptionPreferenceSerializer(read_only=True)

    class Meta:
        model = LifestyleSubscription
        fields = [
            "id",
            "reservation",
            "plan",
            "plan_name",
            "user",
            "listing_title",
            "start_date",
            "end_date",
            "status",
            "latest_payment",
            "lifestyle_preferences",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user", "created_at", "updated_at"]

    def get_latest_payment(self, obj):
        p = obj.subscription_payments.order_by("-created_at").first()
        if not p:
            return None
        return {
            "id": p.id,
            "status": p.status,
            "amount": str(p.amount),
            "currency": p.currency,
            "transaction_id": p.transaction_id,
        }


class LifestyleSubscriptionManagementSerializer(serializers.ModelSerializer):
    """Staff-facing subscription row for the lifestyle management dashboard."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    plan_tier = serializers.IntegerField(source="plan.tier", read_only=True)
    listing_title = serializers.CharField(
        source="reservation.listing.title", read_only=True
    )
    reservation_id = serializers.IntegerField(source="reservation.id", read_only=True)
    latest_payment = serializers.SerializerMethodField()

    class Meta:
        model = LifestyleSubscription
        fields = [
            "id",
            "user_email",
            "plan_name",
            "plan_tier",
            "listing_title",
            "reservation_id",
            "status",
            "start_date",
            "end_date",
            "created_at",
            "latest_payment",
        ]

    def get_latest_payment(self, obj):
        p = obj.subscription_payments.order_by("-created_at").first()
        if not p:
            return None
        return {
            "id": p.id,
            "status": p.status,
            "amount": str(p.amount),
            "currency": p.currency,
            "transaction_id": p.transaction_id,
        }


class LifestyleSubscriptionCreateSerializer(serializers.Serializer):
    # Include "completed" (lister marked stay finished) so renters who already show
    # "Rented" can still subscribe while the lease window is active. Past end_date
    # is rejected in validate().
    reservation_id = serializers.PrimaryKeyRelatedField(
        queryset=Reservation.objects.filter(
            status__in=["pending", "confirmed", "completed"]
        )
    )
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=LifestylePlan.objects.filter(is_active=True)
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        request = self.context["request"]
        reservation = attrs["reservation_id"]
        if reservation.user != request.user:
            raise serializers.ValidationError(
                {"reservation_id": "Reservation must belong to you."}
            )
        if not UAEIDVerification.objects.filter(
            user=request.user, status="approved"
        ).exists():
            raise serializers.ValidationError(
                {
                    "detail": "UAE ID verification must be approved before subscribing to lifestyle services."
                }
            )
        today = timezone.now().date()
        if reservation.end_date and reservation.end_date < today:
            raise serializers.ValidationError(
                {
                    "reservation_id": (
                        "This reservation's stay has ended (past the lease end date). "
                        "Lifestyle add-ons apply only to active or upcoming stays."
                    )
                }
            )
        plan = attrs["plan_id"]
        if LifestyleSubscription.objects.filter(
            reservation=reservation,
            plan=plan,
            user=request.user,
            status="active",
        ).exists():
            raise serializers.ValidationError(
                {
                    "plan_id": "You already have an active subscription for this plan on this reservation."
                }
            )
        end = attrs.get("end_date") or getattr(reservation, "end_date", None)
        if end and attrs["start_date"] >= end:
            raise serializers.ValidationError(
                {"end_date": "End date must be after start date."}
            )
        return attrs
