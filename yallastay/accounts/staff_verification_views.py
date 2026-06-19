"""Staff verification API: broker and owner document queues + approve/reject."""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.text_sanitize import sanitize_plain_text

from .models import LandlordProfile, RealtorProfile
from .staff_permissions import IsVerificationStaff
from .verification_checklist import (
    build_landlord_checklist,
    build_realtor_checklist,
    landlord_checklist_complete,
    realtor_checklist_complete,
)

User = get_user_model()


class StaffVerificationDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    message = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )

    def validate_message(self, value):
        return sanitize_plain_text(value or "")


def _realtor_queue_row(user: User) -> dict:
    rp = user.realtor_profile
    checklist = build_realtor_checklist(user)
    complete = realtor_checklist_complete(user)
    return {
        "user_id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": "realtor",
        "is_approved": rp.is_approved,
        "approved_at": rp.approved_at.isoformat() if rp.approved_at else None,
        "agency_name": rp.agency_name,
        "brokerage_type": rp.brokerage_type,
        "rera_number": rp.rera_number or "",
        "orn": rp.orn or "",
        "checklist": checklist,
        "checklist_complete": complete,
        "license_document_uploaded": bool(rp.license_document),
    }


def _landlord_queue_row(user: User) -> dict:
    lp = user.landlord_profile
    checklist = build_landlord_checklist(user)
    complete = landlord_checklist_complete(user)
    return {
        "user_id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": "landlord",
        "is_approved": lp.is_approved,
        "approved_at": lp.approved_at.isoformat() if lp.approved_at else None,
        "company_name": lp.company_name or "",
        "is_emirati": lp.is_emirati,
        "needs_assisted_listing": lp.needs_assisted_listing,
        "checklist": checklist,
        "checklist_complete": complete,
    }


class StaffVerificationQueueView(APIView):
    """
    GET: Pending broker and owner accounts for document review.

    Rows include a **checklist** (required vs uploaded) and ``checklist_complete``.
    Staff may still approve with an incomplete checklist (business override); the UI warns first.
    """

    permission_classes = [IsAuthenticated, IsVerificationStaff]

    def get(self, request):
        realtor_profiles = (
            RealtorProfile.objects.filter(is_approved=False)
            .select_related("user", "user__profile")
            .order_by("created_at")
        )
        landlord_profiles = (
            LandlordProfile.objects.filter(is_approved=False)
            .select_related("user", "user__profile")
            .order_by("created_at")
        )
        realtors = []
        for rp in realtor_profiles:
            if getattr(rp.user.profile, "role", None) == "realtor":
                realtors.append(_realtor_queue_row(rp.user))
        landlords = []
        for lp in landlord_profiles:
            if getattr(lp.user.profile, "role", None) == "landlord":
                landlords.append(_landlord_queue_row(lp.user))
        return Response({"realtors": realtors, "landlords": landlords})


class StaffRealtorDecisionView(APIView):
    permission_classes = [IsAuthenticated, IsVerificationStaff]

    def post(self, request, user_id):
        user = User.objects.filter(pk=user_id, profile__role="realtor").first()
        if not user:
            return Response(
                {"detail": "Realtor not found."}, status=status.HTTP_404_NOT_FOUND
            )
        ser = StaffVerificationDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        action = ser.validated_data["action"]
        message = ser.validated_data.get("message") or ""

        try:
            rp = user.realtor_profile
        except RealtorProfile.DoesNotExist:
            return Response(
                {"detail": "No realtor profile."}, status=status.HTTP_404_NOT_FOUND
            )

        if action == "approve":
            if not rp.is_approved:
                rp.is_approved = True
                rp.approved_at = timezone.now()
                rp.save()
            return Response({"detail": "approved", "user_id": user.id})

        # reject
        if rp.is_approved:
            rp.is_approved = False
            rp.approved_at = None
            rp.save()
        from notifications.services import notify_user

        body = (
            message
            or "Please review the required documents and resubmit from your profile."
        )
        notify_user(
            user,
            "general",
            "Broker verification needs attention",
            body=body,
            link="/profile",
        )
        return Response({"detail": "rejected", "user_id": user.id})


class StaffLandlordDecisionView(APIView):
    permission_classes = [IsAuthenticated, IsVerificationStaff]

    def post(self, request, user_id):
        user = User.objects.filter(pk=user_id, profile__role="landlord").first()
        if not user:
            return Response(
                {"detail": "Landlord not found."}, status=status.HTTP_404_NOT_FOUND
            )
        ser = StaffVerificationDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        action = ser.validated_data["action"]
        message = ser.validated_data.get("message") or ""

        try:
            lp = user.landlord_profile
        except LandlordProfile.DoesNotExist:
            return Response(
                {"detail": "No landlord profile."}, status=status.HTTP_404_NOT_FOUND
            )

        if action == "approve":
            if not lp.is_approved:
                lp.is_approved = True
                lp.approved_at = timezone.now()
                lp.save()
            return Response({"detail": "approved", "user_id": user.id})

        if lp.is_approved:
            lp.is_approved = False
            lp.approved_at = None
            lp.save()
        from notifications.services import notify_user

        body = (
            message
            or "Please upload the required owner documents and try again from your profile."
        )
        notify_user(
            user,
            "general",
            "Owner verification needs attention",
            body=body,
            link="/profile",
        )
        return Response({"detail": "rejected", "user_id": user.id})
