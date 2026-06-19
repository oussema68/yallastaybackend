from rest_framework import serializers
from .models import Payment
from bookings.models import Reservation


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "amount",
            "currency",
            "payment_type",
            "status",
            "payment_method",
            "transaction_id",
            "reservation",
            "lifestyle_subscription",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user", "created_at", "updated_at"]


class PaymentInitiateSerializer(serializers.Serializer):
    """Initiate payment. Returns checkout URL / client_secret for frontend."""

    payment_type = serializers.ChoiceField(
        choices=["rent", "deposit", "fee", "lifestyle"]
    )
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    currency = serializers.CharField(default="AED", max_length=3)
    reservation_id = serializers.PrimaryKeyRelatedField(
        queryset=Reservation.objects.all(), required=False, allow_null=True
    )
    # Optional: rent_schedule_id or deposit_id for linking

    def validate(self, attrs):
        if attrs["payment_type"] in ("rent", "deposit", "lifestyle") and not attrs.get(
            "reservation_id"
        ):
            raise serializers.ValidationError(
                {
                    "reservation_id": "Required for rent, deposit, and lifestyle payments."
                }
            )

        request = self.context.get("request")
        reservation = attrs.get("reservation_id")
        if reservation is not None and request and request.user.is_authenticated:
            u = request.user
            listing = reservation.listing
            is_renter = reservation.user_id == u.id
            is_lister = listing.listed_by_id == u.id
            is_owner = bool(
                listing.property_owner_id and listing.property_owner_id == u.id
            )
            if not (is_renter or is_lister or is_owner):
                raise serializers.ValidationError(
                    {"reservation_id": "You do not have access to this reservation."}
                )
            ptype = attrs["payment_type"]
            if ptype in ("rent", "deposit", "lifestyle") and not is_renter:
                raise serializers.ValidationError(
                    {
                        "reservation_id": (
                            "Only the renter on this booking can start rent, deposit, "
                            "or lifestyle payments for this reservation."
                        )
                    }
                )

        return attrs
