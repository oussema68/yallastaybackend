import hashlib
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .emails import send_uae_id_submitted_emails
from .models import UAEIDVerification, UniversityVerification
from .serializers import (
    UAEIDVerificationSerializer,
    UniversityVerificationSerializer,
)


class UAEIDVerificationView(APIView):
    """POST: Submit UAE ID + document for verification."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UAEIDVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        emirates_id = serializer.validated_data["emirates_id"]
        document = serializer.validated_data.get("document")

        id_hash = hashlib.sha256(emirates_id.encode()).hexdigest()

        defaults = {
            "id_hash": id_hash,
            "status": "pending",
            "verified_at": None,
        }
        if document:
            defaults["document"] = document

        UAEIDVerification.objects.update_or_create(user=request.user, defaults=defaults)

        send_uae_id_submitted_emails(request.user, has_document=bool(document))

        return Response(
            {"message": "UAE ID verification submitted. Awaiting admin approval."},
            status=status.HTTP_201_CREATED,
        )


class UniversityVerificationView(APIView):
    """POST: Submit university email for student verification."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UniversityVerificationSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        university = serializer.validated_data["university_id"]
        student_id = serializer.validated_data.get("student_id", "")

        obj, created = UniversityVerification.objects.update_or_create(
            user=request.user,
            defaults={
                "email": email,
                "university": university,
                "student_id": student_id,
                "status": "pending",
                "verified_at": None,
            },
        )

        return Response(
            {
                "message": "University verification submitted. Check your email for verification link."
            },
            status=status.HTTP_201_CREATED,
        )


class VerificationStatusView(APIView):
    """GET: Current user's verification status."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        uae_status = None
        uae_verified = False
        try:
            uae = request.user.uae_id_verification
            uae_status = uae.status
            uae_verified = uae.status == "approved"
        except UAEIDVerification.DoesNotExist:
            pass

        uni_status = None
        uni_verified = False
        try:
            uni = request.user.university_verification
            uni_status = uni.status
            uni_verified = uni.status == "approved"
        except UniversityVerification.DoesNotExist:
            pass

        data = {
            "uae_id_verified": uae_verified,
            "uae_id_status": uae_status,
            "university_verified": uni_verified,
            "university_status": uni_status,
        }
        return Response(data)
