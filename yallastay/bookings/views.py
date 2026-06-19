from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.permissions import IsUAEIDVerified
from listings.models import Listing
from notifications.services import notify_user
from .party import reservation_party
from .models import ViewingRequest, Reservation
from .serializers import (
    ViewingRequestSerializer,
    ViewingRequestCreateSerializer,
    ViewingRequestUpdateSerializer,
    ReservationSerializer,
    ReservationCreateSerializer,
    ReservationStatusUpdateSerializer,
    ReservationMoveInUpdateSerializer,
)
from .permissions import CanManageViewing


def _create_reservation(request, validated):
    listing = validated["listing_id"]
    return Reservation.objects.create(
        listing=listing,
        user=request.user,
        start_date=validated["start_date"],
        end_date=validated["end_date"],
        deposit_amount=validated.get("deposit_amount", 0),
        notes=validated.get("notes", ""),
    )


class ViewingRequestListCreateView(APIView):
    """
    GET: List viewings (as tenant: own requests; as landlord/realtor: for own listings).
    POST: Request viewing (requires UAE ID verification).
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsUAEIDVerified()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        try:
            role = user.profile.role
        except Exception:
            role = None

        if role in ["landlord", "realtor"]:
            return ViewingRequest.objects.filter(listing__listed_by=user)
        return ViewingRequest.objects.filter(user=user)

    def get(self, request):
        queryset = self.get_queryset()
        serializer = ViewingRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ViewingRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = serializer.validated_data["listing_id"]
        viewing = ViewingRequest.objects.create(
            listing=listing,
            user=request.user,
            requested_datetime=serializer.validated_data["requested_datetime"],
            notes=serializer.validated_data.get("notes", ""),
        )
        return Response(
            ViewingRequestSerializer(viewing).data, status=status.HTTP_201_CREATED
        )


class ViewingRequestDetailView(APIView):
    """
    GET: Viewing detail.
    PATCH: Confirm/reject (landlord/realtor who listed the property only).
    """

    permission_classes = [IsAuthenticated, CanManageViewing]

    def get_object(self, pk):
        return ViewingRequest.objects.get(pk=pk)

    def get(self, request, pk):
        viewing = self.get_object(pk)
        try:
            role = request.user.profile.role
        except Exception:
            role = None
        if role in ["landlord", "realtor"]:
            if viewing.listing.listed_by != request.user:
                return Response(
                    {"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            if viewing.user != request.user:
                return Response(
                    {"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND
                )
        return Response(ViewingRequestSerializer(viewing).data)

    def patch(self, request, pk):
        viewing = self.get_object(pk)
        if viewing.listing.listed_by != request.user:
            return Response(
                {"detail": "Only the lister can confirm or reject."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ViewingRequestUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        viewing.status = serializer.validated_data["status"]
        viewing.save()
        return Response(ViewingRequestSerializer(viewing).data)


class ReservationListCreateView(APIView):
    """
    GET: List reservations (as tenant: own; as landlord/realtor: for own listings).
    POST: Create reservation (requires UAE ID verification).
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsUAEIDVerified()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        try:
            role = user.profile.role
        except Exception:
            role = None

        if role in ["landlord", "realtor"]:
            return Reservation.objects.filter(listing__listed_by=user)
        return Reservation.objects.filter(user=user)

    def get(self, request):
        queryset = (
            self.get_queryset()
            .select_related(
                "listing",
                "listing__area",
                "listing__listed_by",
                "user",
                "lease_signing",
            )
            .order_by("-updated_at", "-created_at")
        )
        serializer = ReservationSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request):
        serializer = ReservationCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        reservation = _create_reservation(request, serializer.validated_data)
        return Response(
            ReservationSerializer(reservation, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class RentFromAppView(APIView):
    """
    POST: Create a rental request for a listing (same rules as POST /api/reservations/).
    Intended for the property page CTA; listing id comes from the URL.
    """

    permission_classes = [IsAuthenticated, IsUAEIDVerified]

    def post(self, request, listing_id):
        listing = get_object_or_404(Listing, pk=listing_id)
        data = {**request.data, "listing_id": listing.id}
        serializer = ReservationCreateSerializer(
            data=data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        reservation = _create_reservation(request, serializer.validated_data)
        return Response(
            ReservationSerializer(reservation, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ReservationDetailView(APIView):
    """GET: Reservation detail. PATCH: Update status (lister confirms/completes; either party can cancel)."""

    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Reservation.objects.select_related(
                "listing", "listing__listed_by", "user", "lease_signing"
            ),
            pk=pk,
        )

    def _get_reservation_for_user(self, request, pk):
        reservation = self.get_object(pk)
        party = reservation_party(request, reservation)
        if party is None:
            return None, Response(
                {"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return reservation, None

    def get(self, request, pk):
        reservation, err = self._get_reservation_for_user(request, pk)
        if err:
            return err
        return Response(
            ReservationSerializer(reservation, context={"request": request}).data
        )

    def patch(self, request, pk):
        reservation, err = self._get_reservation_for_user(request, pk)
        if err:
            return err
        serializer = ReservationStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]

        if reservation.status in ("cancelled", "completed"):
            return Response(
                {"detail": "This reservation can no longer be updated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        party = reservation_party(request, reservation)

        if new_status == "confirmed":
            if party != "lister" or reservation.status != "pending":
                return Response(
                    {"detail": "Only the lister can confirm a pending request."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif new_status == "completed":
            if party != "lister" or reservation.status != "confirmed":
                return Response(
                    {
                        "detail": "Only the lister can mark a confirmed stay as completed."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif new_status == "cancelled":
            if party not in ("lister", "renter"):
                return Response(
                    {"detail": "Not allowed."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            return Response(
                {"detail": "Invalid status transition."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reservation.status = new_status
        reservation.save()

        if new_status == "cancelled":
            from payments.models import Payment

            Payment.objects.filter(
                reservation=reservation,
                status="pending",
            ).update(status="cancelled")

        if new_status == "confirmed":
            listing = reservation.listing
            renter = reservation.user
            lister = listing.listed_by
            notify_user(
                renter,
                "acceptance",
                "Rental request accepted",
                f"Your request for “{listing.title}” was accepted. Coordinate next steps in Messages.",
                link=f"/property/{listing.id}",
            )
            notify_user(
                renter,
                "contract",
                "Tenancy & contract",
                "Formal Ejari / tenancy paperwork may follow by email or through your lister. Check Messages.",
                link="/messages",
            )
            notify_user(
                lister,
                "acceptance",
                "You confirmed a rental request",
                f"You accepted {renter.email}'s request for “{listing.title}”.",
                link="/dashboard",
            )

        return Response(
            ReservationSerializer(reservation, context={"request": request}).data
        )


class ReservationMoveInView(APIView):
    """
    PATCH: Renter confirms keys handover and/or submits private platform feedback.

    Available when the reservation is **confirmed** or **completed**.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        reservation = get_object_or_404(
            Reservation.objects.select_related(
                "listing",
                "listing__listed_by",
                "user",
                "lease_signing",
            ),
            pk=pk,
        )
        if reservation.user_id != request.user.id:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if reservation.status not in ("confirmed", "completed"):
            return Response(
                {
                    "detail": (
                        "Move-in check-in is available once your booking is confirmed "
                        "or completed."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReservationMoveInUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        had_keys = reservation.keys_received_at is not None
        if serializer.validated_data.get("keys_received") is True:
            if reservation.keys_received_at is None:
                reservation.keys_received_at = timezone.now()

        if "platform_feedback" in serializer.validated_data:
            reservation.platform_feedback = serializer.validated_data[
                "platform_feedback"
            ]

        reservation.save()

        if serializer.validated_data.get("keys_received") is True and not had_keys:
            listing = reservation.listing
            lister = listing.listed_by
            renter = reservation.user
            label = (renter.get_full_name() or "").strip() or renter.email
            notify_user(
                lister,
                "booking",
                "Renter confirmed key handover",
                f"{label} confirmed they collected keys for “{listing.title}”.",
                link="/dashboard",
            )

        return Response(
            ReservationSerializer(reservation, context={"request": request}).data
        )
