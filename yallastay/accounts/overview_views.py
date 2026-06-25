"""Single round-trip payload for account dashboard / header badges."""

from __future__ import annotations

from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UAEIDVerification, UniversityVerification
from accounts.serializers import UserSerializer
from analytics.views import MyListingsInsightsView
from bookings.models import Reservation, ViewingRequest
from bookings.serializers import ReservationSerializer, ViewingRequestSerializer
from core.query_window import apply_limit_offset
from listings.models import Favorite, Listing
from listings.serializers import FavoriteSerializer, ListingListSerializer
from messaging.models import Message
from notifications.models import Notification
from payments.models import Payment
from payments.serializers import PaymentSerializer
from reviews.models import Review
from reviews.serializers import ReviewSerializer


def _verification_payload(user) -> dict:
    uae_status = None
    uae_verified = False
    try:
        uae = user.uae_id_verification
        uae_status = uae.status
        uae_verified = uae.status == "approved"
    except UAEIDVerification.DoesNotExist:
        pass

    uni_status = None
    uni_verified = False
    try:
        uni = user.university_verification
        uni_status = uni.status
        uni_verified = uni.status == "approved"
    except UniversityVerification.DoesNotExist:
        pass

    return {
        "uae_id_verified": uae_verified,
        "uae_id_status": uae_status,
        "university_verified": uni_verified,
        "university_status": uni_status,
    }


class AccountOverviewView(APIView):
    """
    GET: One response for dashboard shell — user, verification, unread badges,
    and capped previews (avoids 8+ parallel round-trips from the SPA).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        ctx = {"request": request}

        role = None
        try:
            role = user.profile.role
        except Exception:
            pass

        unread_messages = (
            Message.objects.filter(
                conversation__participants=user,
                read_at__isnull=True,
            )
            .exclude(sender=user)
            .count()
        )
        unread_notifications = Notification.objects.filter(
            user=user, read=False
        ).count()

        if role in ("landlord", "realtor"):
            reservations_qs = Reservation.objects.filter(listing__listed_by=user)
            viewings_qs = ViewingRequest.objects.filter(listing__listed_by=user)
        else:
            reservations_qs = Reservation.objects.filter(user=user)
            viewings_qs = ViewingRequest.objects.filter(user=user)

        reservations_qs = reservations_qs.select_related(
            "listing", "listing__area", "listing__listed_by", "user", "lease_signing"
        )
        reservations_qs = apply_limit_offset(
            reservations_qs.order_by("-created_at"),
            request,
            default_limit=50,
            max_limit=50,
        )
        reservations = ReservationSerializer(
            reservations_qs, many=True, context=ctx
        ).data

        viewings_qs = viewings_qs.select_related(
            "listing", "listing__area", "listing__listed_by", "user"
        )
        viewings_qs = apply_limit_offset(
            viewings_qs.order_by("-created_at"),
            request,
            default_limit=50,
            max_limit=50,
        )
        viewings = ViewingRequestSerializer(viewings_qs, many=True, context=ctx).data

        favorites = []
        if role in ("tenant", "student"):
            fav_qs = (
                Favorite.objects.filter(user=user)
                .select_related("listing", "listing__area")
                .prefetch_related("listing__images")[:50]
            )
            favorites = FavoriteSerializer(fav_qs, many=True, context=ctx).data

        payments_qs = Payment.objects.filter(user=user).order_by("-created_at")
        payments_qs = apply_limit_offset(
            payments_qs,
            request,
            default_limit=15,
            max_limit=15,
        )
        payments = PaymentSerializer(payments_qs, many=True, context=ctx).data

        reviews_qs = Review.objects.filter(reviewee=user).select_related(
            "reviewer", "listing"
        )
        reviews_qs = apply_limit_offset(
            reviews_qs.order_by("-created_at"),
            request,
            default_limit=20,
            max_limit=20,
        )
        reviews = ReviewSerializer(reviews_qs, many=True, context=ctx).data

        listings_insights = None
        my_listings = []
        if role in ("landlord", "realtor"):
            insights_view = MyListingsInsightsView()
            insights_response = insights_view.get(request)
            listings_insights = insights_response.data

            if role == "realtor":
                mine_qs = Listing.objects.filter(
                    Q(listed_by=user) | Q(assigned_realtor=user),
                    status="active",
                )
            elif role == "landlord":
                mine_qs = Listing.objects.filter(
                    Q(listed_by=user) | Q(property_owner=user),
                    status="active",
                )
            else:
                mine_qs = Listing.objects.none()

            mine_qs = mine_qs.select_related(
                "area",
                "listed_by",
                "assigned_realtor__realtor_profile",
            ).prefetch_related("images")[:60]
            my_listings = ListingListSerializer(mine_qs, many=True, context=ctx).data

        return Response(
            {
                "user": UserSerializer(user).data,
                "verification": _verification_payload(user),
                "unread_messages": unread_messages,
                "unread_notifications": unread_notifications,
                "reservations": reservations,
                "viewings": viewings,
                "favorites": favorites,
                "payments": payments,
                "reviews": reviews,
                "listings_insights": listings_insights,
                "my_listings": my_listings,
            }
        )
