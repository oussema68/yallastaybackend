"""Read-only public profile for trust (reviews, verification) and lister contract context."""

import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.media_urls import absolute_media_url
from bookings.models import Reservation, ViewingRequest
from messaging.models import Conversation
from messaging.team_user import is_yallastay_team_user
from reviews.models import Review

User = get_user_model()

logger = logging.getLogger(__name__)


def _viewer_can_see_contract_fields(viewer, subject) -> bool:
    """Lister/realtor: phone & similar only when there is a real relationship."""
    if viewer.pk == subject.pk:
        return True
    try:
        role = viewer.profile.role
    except Exception:
        role = None
    if role not in ("landlord", "realtor"):
        return False
    if (
        Conversation.objects.filter(participants=viewer)
        .filter(participants=subject)
        .exists()
    ):
        return True
    if Reservation.objects.filter(user=subject, listing__listed_by=viewer).exists():
        return True
    if ViewingRequest.objects.filter(user=subject, listing__listed_by=viewer).exists():
        return True
    return False


def _verification_flags(user):
    profile = getattr(user, "profile", None)
    email_verified = bool(profile and profile.is_email_verified)
    uae = getattr(user, "uae_id_verification", None)
    uae_verified = bool(uae and uae.status == "approved")
    uni = getattr(user, "university_verification", None)
    uni_verified = bool(uni and uni.status == "approved")
    return {
        "email_verified": email_verified,
        "uae_id_verified": uae_verified,
        "university_verified": uni_verified,
    }


def _last_name_initial(user) -> str:
    last = (user.last_name or "").strip()
    return (last[0] + ".").upper() if last else ""


def _reviewer_label(reviewer) -> str:
    try:
        role = reviewer.profile.role
        if role in ("tenant", "student"):
            return "Verified renter"
        if role in ("landlord", "realtor"):
            return "Property professional"
    except Exception:
        pass
    return "Member"


def _serialize_review(r):
    response_payload = None
    try:
        resp = r.response
        response_payload = {
            "response_text": resp.response_text,
            "created_at": resp.created_at,
        }
    except ObjectDoesNotExist:
        pass
    return {
        "id": r.id,
        "rating": r.rating,
        "comment": r.comment,
        "created_at": r.created_at,
        "listing_title": r.listing.title if r.listing_id else None,
        "reviewer_label": _reviewer_label(r.reviewer),
        "response": response_payload,
    }


class PublicUserProfileView(APIView):
    """
    GET: Minimal profile + reviews + optional contract context for listers.

    Authenticated users only. Emails are never exposed.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = get_object_or_404(
            User.objects.select_related(
                "profile",
                "profile__work_area",
                "realtor_profile",
                "uae_id_verification",
                "university_verification",
            ),
            pk=pk,
        )
        if is_yallastay_team_user(user):
            logger.info(
                "accounts.public_profile.blocked_team: viewer_id=%s subject_id=%s",
                request.user.id,
                pk,
            )
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        profile = getattr(user, "profile", None)
        role = profile.role if profile else "tenant"

        last_initial = _last_name_initial(user)
        avatar_url = None
        if profile and profile.avatar:
            try:
                avatar_url = absolute_media_url(request, profile.avatar)
            except Exception:
                avatar_url = None

        base = {
            "id": user.id,
            "first_name": (user.first_name or "").strip() or "User",
            "last_name_initial": last_initial,
            "role": role,
            "member_since": (
                user.date_joined.date().isoformat() if user.date_joined else None
            ),
            "avatar_url": avatar_url,
            "verification": _verification_flags(user),
        }

        # Reviews about this user (past rentals / interactions)
        qs = Review.objects.filter(reviewee=user).select_related(
            "listing", "reviewer", "reviewer__profile"
        )
        agg_all = qs.aggregate(avg=Avg("rating"), count=Count("id"))
        renter_qs = qs.filter(
            Q(reviewer__profile__role="tenant") | Q(reviewer__profile__role="student")
        )
        agg_renters = renter_qs.aggregate(avg=Avg("rating"), count=Count("id"))

        review_summary = {
            "average_rating": (
                round(agg_all["avg"], 2) if agg_all["avg"] is not None else None
            ),
            "count": agg_all["count"] or 0,
        }
        renter_review_summary = {
            "average_rating": (
                round(agg_renters["avg"], 2) if agg_renters["avg"] is not None else None
            ),
            "count": agg_renters["count"] or 0,
            "description": "Reviews from renters (tenants and students)",
        }

        reviews_list = [
            _serialize_review(r)
            for r in qs.prefetch_related("response").order_by("-created_at")[:30]
        ]

        base["review_summary"] = review_summary
        base["renter_review_summary"] = renter_review_summary
        base["reviews"] = reviews_list

        # Realtor / landlord public trust fields (no raw license files)
        if role == "realtor":
            try:
                rp = user.realtor_profile
                base["realtor_public"] = {
                    "agency_name": rp.agency_name,
                    "is_approved": rp.is_approved,
                    "rera_number": (rp.rera_number or "").strip(),
                    "orn": (rp.orn or "").strip(),
                }
            except Exception:
                base["realtor_public"] = None
        else:
            base["realtor_public"] = None

        # Contract-oriented fields for listers with a relationship to this user
        base["contract_context"] = None
        if _viewer_can_see_contract_fields(request.user, user):
            ctx = {
                "shared_because": "You have a conversation, booking, or viewing with this person.",
            }
            if profile:
                ctx["phone"] = (profile.phone or "").strip() or None
                if role in ("tenant", "student"):
                    ctx["place_of_work_or_studies"] = (
                        profile.place_of_work_or_studies or ""
                    ).strip() or None
                    ctx["work_area"] = (
                        profile.work_area.name if profile.work_area_id else None
                    )
                ctx["bio"] = (profile.bio or "").strip()[:500] or None
            base["contract_context"] = ctx

        logger.info(
            "accounts.public_profile.ok: viewer_id=%s subject_id=%s role=%s contract=%s",
            request.user.id,
            pk,
            role,
            base["contract_context"] is not None,
        )
        return Response(base)
