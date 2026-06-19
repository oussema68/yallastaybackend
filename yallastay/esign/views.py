import logging

from django.conf import settings
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import (
    UAE_ELECTRONIC_CONSENT_VERSION,
    consent_required_for_request,
    record_lease_sign_audit,
    role_for_token,
    token_fingerprint,
    truthy_consent,
)
from .models import LeaseSigningAuditEvent, LeaseSigningSession
from .serializers import LeaseSigningSessionSerializer
from .services import preview_sign_token, session_has_contract_pdf, sign_with_token
from .signature_boxes import normalize_signature_field_boxes, validate_boxes_fit_pdf
from .signature_utils import decode_signature_png_payload


def _signature_error_messages():
    """User-facing strings; max signature size follows ``ESIGN_SIGNATURE_MAX_BYTES``."""
    max_kb = max(1, int(settings.ESIGN_SIGNATURE_MAX_BYTES) // 1024)
    return {
        "missing_signature": "Draw your signature in the box, then submit.",
        "signature_too_small": "Signature image is too small - try a clearer stroke.",
        "signature_too_large": f"Signature image is too large (max {max_kb} KB).",
        "invalid_signature_format": "Signature must be a valid PNG image.",
        "invalid_signature_dimensions": "Signature image size is not allowed.",
        "missing_slot_index": "This lease uses multiple signature areas - use the signing page’s guided steps.",
        "invalid_slot_index": "Invalid signature placement index.",
        "slot_order": "Sign each highlighted area in order before moving to the next.",
        "missing_signature_placements": (
            "The landlord side must place signature fields on the lease PDF "
            "before you can sign."
        ),
        "consent_required": (
            "You must agree to use electronic records and signatures under UAE law "
            "(Federal Decree-Law No. 46 of 2021) before signing."
        ),
    }


logger = logging.getLogger(__name__)


def _lease_session_access_q(uid):
    return (
        Q(reservation__user_id=uid)
        | Q(reservation__listing__listed_by_id=uid)
        | Q(reservation__listing__property_owner_id=uid)
    )


def _may_manage_lease_upload_or_boxes(session, user) -> bool:
    """Listing creator (e.g. realtor) or property owner may upload PDF and place signature fields."""
    listing = session.reservation.listing
    if user.id == listing.listed_by_id:
        return True
    if listing.property_owner_id and user.id == listing.property_owner_id:
        return True
    return False


@method_decorator(xframe_options_exempt, name="dispatch")
class LeaseSigningPdfView(APIView):
    """GET: PDF for magic-link token (contract, or merged signed PDF). No JWT."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        token = (token or "").strip()
        if not token:
            return Response(
                {"detail": "Invalid link."}, status=status.HTTP_404_NOT_FOUND
            )
        session = LeaseSigningSession.objects.filter(
            Q(renter_token=token) | Q(lister_token=token)
        ).first()
        if not session:
            return Response(
                {"detail": "Invalid or expired link."}, status=status.HTTP_404_NOT_FOUND
            )
        if session.status == "cancelled":
            return Response(
                {"detail": "This signing request was cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            record_lease_sign_audit(
                session,
                event_type=LeaseSigningAuditEvent.EventType.CONTRACT_PDF_VIEWED,
                request=request,
                actor_role=role_for_token(session, token),
                metadata={
                    "token_fp": token_fingerprint(token),
                    "pdf_kind": "signed" if session.signed_pdf else "contract",
                },
            )
        except Exception:
            logger.exception("esign.audit.pdf_view session_id=%s", session.pk)
        pdf_file = (
            session.signed_pdf
            if session.signed_pdf
            else (session.lister_contract_pdf or session.contract_pdf)
        )
        if not pdf_file:
            return Response(
                {"detail": "PDF not available yet."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            fh = pdf_file.open("rb")
        except Exception:
            logger.exception("esign.pdf.open_failed session_id=%s", session.pk)
            return Response(
                {"detail": "Could not read PDF."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return FileResponse(
            fh,
            content_type="application/pdf",
            as_attachment=False,
            filename=f"lease-session-{session.pk}.pdf",
        )


class LeaseSigningSessionContractPdfView(APIView):
    """
    GET: Same lease PDF as the magic-link /esign/sign/:token/pdf/ endpoint, but for
    authenticated dashboard use (JWT). Avoids putting signing tokens in fetch URLs.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        uid = request.user.id
        session = get_object_or_404(
            LeaseSigningSession.objects.select_related(
                "reservation",
                "reservation__listing",
                "reservation__listing__listed_by",
                "reservation__listing__property_owner",
            ).filter(_lease_session_access_q(uid)),
            pk=pk,
        )
        pdf_file = (
            session.signed_pdf
            if session.signed_pdf
            else (session.lister_contract_pdf or session.contract_pdf)
        )
        if not pdf_file:
            return Response(
                {"detail": "PDF not available yet."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            fh = pdf_file.open("rb")
        except Exception:
            logger.exception("esign.session_pdf.open_failed session_id=%s", session.pk)
            return Response(
                {"detail": "Could not read PDF."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return FileResponse(
            fh,
            content_type="application/pdf",
            as_attachment=False,
            filename=f"lease-session-{session.pk}.pdf",
        )


class LeaseSigningSessionListView(APIView):
    """GET: Sessions where the current user is renter or lister."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        uid = request.user.id
        qs = (
            LeaseSigningSession.objects.filter(_lease_session_access_q(uid))
            .select_related(
                "reservation",
                "reservation__listing",
                "reservation__listing__listed_by",
                "reservation__listing__property_owner",
            )
            .order_by("-created_at")
        )
        ser = LeaseSigningSessionSerializer(qs, many=True, context={"request": request})
        logger.info("esign.list: user_id=%s count=%s", uid, len(ser.data))
        return Response(ser.data)


class LeaseSigningSessionDetailView(APIView):
    """GET: One session if user is renter or lister."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        uid = request.user.id
        session = get_object_or_404(
            LeaseSigningSession.objects.select_related(
                "reservation",
                "reservation__listing",
                "reservation__listing__listed_by",
                "reservation__listing__property_owner",
            ).filter(_lease_session_access_q(uid)),
            pk=pk,
        )
        return Response(
            LeaseSigningSessionSerializer(session, context={"request": request}).data
        )


class LeaseSigningUploadContractView(APIView):
    """POST: Listing owner uploads the tenancy contract PDF (before renter signs)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        session = get_object_or_404(
            LeaseSigningSession.objects.select_related(
                "reservation",
                "reservation__listing",
                "reservation__listing__listed_by",
                "reservation__listing__property_owner",
            ),
            pk=pk,
        )
        if not _may_manage_lease_upload_or_boxes(session, request.user):
            return Response(
                {"detail": "You do not have permission to upload for this lease."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if session.status != "pending":
            return Response(
                {"detail": "This signing session is not accepting uploads."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if session.renter_signed_at:
            return Response(
                {
                    "detail": "The contract cannot be replaced after the renter has signed.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"detail": 'Send the PDF as multipart field "file".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        max_bytes = int(settings.ESIGN_LEASE_UPLOAD_MAX_BYTES)
        if upload.size > max_bytes:
            max_mb = max(1, max_bytes // (1024 * 1024))
            return Response(
                {"detail": f"File too large (max {max_mb} MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        head = upload.read(5)
        upload.seek(0)
        if not head.startswith(b"%PDF"):
            return Response(
                {"detail": "Only PDF files are accepted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if session.lister_contract_pdf:
            session.lister_contract_pdf.delete(save=False)
        fname = f"lister-lease-{session.pk}.pdf"
        session.lister_contract_pdf.save(fname, ContentFile(upload.read()), save=False)
        meta = dict(session.provider_metadata or {})
        meta["contract_source"] = "lister_upload"
        session.provider_metadata = meta
        session.signature_field_boxes = {}
        if session.signed_pdf:
            session.signed_pdf.delete(save=False)
            session.signed_pdf = None
        session.save(
            update_fields=[
                "lister_contract_pdf",
                "provider_metadata",
                "signature_field_boxes",
                "signed_pdf",
                "updated_at",
            ]
        )
        try:
            from esign.pdf_service import rebuild_signed_pdf

            rebuild_signed_pdf(session)
        except Exception:
            logger.exception("esign.rebuild_after_upload session_id=%s", session.pk)
        session.refresh_from_db()
        logger.info(
            "esign.lister_contract_uploaded session_id=%s user_id=%s",
            session.pk,
            request.user.id,
        )
        return Response(
            LeaseSigningSessionSerializer(session, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class LeaseSigningSignatureFieldsView(APIView):
    """
    PATCH: Listing owner / realtor sets where renter and lister signatures appear on the contract PDF.
    Coordinates are PDF points, origin bottom-left (same as ReportLab). Cleared when a new PDF is uploaded.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        session = get_object_or_404(
            LeaseSigningSession.objects.select_related(
                "reservation",
                "reservation__listing",
                "reservation__listing__listed_by",
                "reservation__listing__property_owner",
            ),
            pk=pk,
        )
        if not _may_manage_lease_upload_or_boxes(session, request.user):
            return Response(
                {"detail": "You do not have permission to update signature fields."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if session.status != "pending":
            return Response(
                {"detail": "This signing session does not accept field updates."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if session.renter_signed_at:
            return Response(
                {
                    "detail": "Signature fields cannot be changed after the renter has signed.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        raw = request.data.get("signature_field_boxes")
        if raw in (None, {}, []):
            session.signature_field_boxes = {}
            if session.signed_pdf:
                session.signed_pdf.delete(save=False)
                session.signed_pdf = None
            session.save(
                update_fields=["signature_field_boxes", "signed_pdf", "updated_at"]
            )
            try:
                from esign.pdf_service import rebuild_signed_pdf

                rebuild_signed_pdf(session)
            except Exception:
                logger.exception(
                    "esign.rebuild_after_clear_boxes session_id=%s", session.pk
                )
            session.refresh_from_db()
            return Response(
                LeaseSigningSessionSerializer(
                    session, context={"request": request}
                ).data
            )

        if not session_has_contract_pdf(session):
            return Response(
                {"detail": "Upload the lease PDF before setting signature fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        norm = normalize_signature_field_boxes(raw)
        if not norm:
            return Response(
                {
                    "detail": (
                        "Provide signature_field_boxes: renter and lister as arrays of "
                        "three rects each (or empty lister while saving renter first). "
                        "Each rect: "
                        '{"page_index": 0, "x": 72, "y": 72, "width": 200, "height": 48} '
                        "(PDF points, bottom-left origin). Legacy single rect per role is still accepted."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        from esign.pdf_service import contract_base_bytes, rebuild_signed_pdf

        pdf_bytes = contract_base_bytes(session)
        if not pdf_bytes:
            return Response(
                {"detail": "Could not read the contract PDF."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        err = validate_boxes_fit_pdf(pdf_bytes, norm)
        if err:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

        session.signature_field_boxes = norm
        if session.signed_pdf:
            session.signed_pdf.delete(save=False)
            session.signed_pdf = None
        session.save(
            update_fields=["signature_field_boxes", "signed_pdf", "updated_at"]
        )
        try:
            rebuild_signed_pdf(session)
        except Exception:
            logger.exception("esign.rebuild_after_boxes session_id=%s", session.pk)
        session.refresh_from_db()
        logger.info(
            "esign.signature_fields_set session_id=%s user_id=%s",
            session.pk,
            request.user.id,
        )
        return Response(
            LeaseSigningSessionSerializer(session, context={"request": request}).data
        )


@method_decorator(csrf_exempt, name="dispatch")
class LeaseSigningSignView(APIView):
    """
    POST: Stub signature - magic link token in URL (no JWT).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        data, err = preview_sign_token(token)
        if err == "not_found":
            return Response({"detail": "Invalid or expired link."}, status=404)
        if err == "cancelled":
            return Response(
                {"detail": "This signing request was cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        t = (token or "").strip()
        if data is not None and t:
            session = LeaseSigningSession.objects.filter(
                Q(renter_token=t) | Q(lister_token=t)
            ).first()
            if session:
                try:
                    record_lease_sign_audit(
                        session,
                        event_type=LeaseSigningAuditEvent.EventType.SIGN_PREVIEW_ACCESSED,
                        request=request,
                        actor_role=role_for_token(session, t),
                        metadata={"token_fp": token_fingerprint(t)},
                    )
                except Exception:
                    logger.exception("esign.audit.preview session_id=%s", session.pk)
        return Response(data)

    def post(self, request, token):
        token = (token or "").strip()
        session = LeaseSigningSession.objects.filter(
            Q(renter_token=token) | Q(lister_token=token)
        ).first()
        if not session:
            return Response({"detail": "Invalid or expired link."}, status=404)
        if session.status == "cancelled":
            return Response(
                {"detail": "This signing request was cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        d = request.data
        if not hasattr(d, "get"):
            d = {}
        role = role_for_token(session, token)
        if consent_required_for_request(session, token, role) and not truthy_consent(
            d.get("consent_to_electronic_signature")
        ):
            return Response(
                {
                    "detail": _signature_error_messages()["consent_required"],
                    "code": "consent_required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        raw = d.get("signature_png") or d.get("signature_png_base64")
        sig_bytes = decode_signature_png_payload(raw) if isinstance(raw, str) else None
        slot_raw = d.get("signature_slot_index")
        sig_slot = None
        if slot_raw is not None and slot_raw != "":
            try:
                sig_slot = int(slot_raw)
            except (TypeError, ValueError):
                sig_slot = None
        need_consent_audit = consent_required_for_request(session, token, role)
        session, err = sign_with_token(
            token,
            signature_png_bytes=sig_bytes,
            signature_slot_index=sig_slot,
        )
        if err == "not_found":
            return Response({"detail": "Invalid or expired link."}, status=404)
        if err == "cancelled":
            return Response(
                {"detail": "This signing request was cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if err == "no_contract_pdf":
            return Response(
                {
                    "detail": "The lease PDF is not available yet. The listing owner must upload it from the dashboard.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if err == "renter_must_sign_first":
            return Response(
                {
                    "detail": "The renter must sign before the landlord can sign.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        _msgs = _signature_error_messages()
        if err in _msgs:
            return Response(
                {
                    "detail": _msgs[err],
                    "code": err,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if err == "already_done":
            return Response(
                {
                    "detail": "Already signed.",
                    "session": LeaseSigningSessionSerializer(
                        session, context={"request": request}
                    ).data,
                },
                status=status.HTTP_200_OK,
            )
        try:
            meta = {
                "token_fp": token_fingerprint(token),
                "signature_slot_index": sig_slot,
                "consent_version": UAE_ELECTRONIC_CONSENT_VERSION,
            }
            if need_consent_audit:
                record_lease_sign_audit(
                    session,
                    event_type=LeaseSigningAuditEvent.EventType.ELECTRONIC_CONSENT_ACCEPTED,
                    request=request,
                    actor_role=role,
                    metadata={**meta, "basis": "UAE Federal Decree-Law No. 46 of 2021"},
                )
            record_lease_sign_audit(
                session,
                event_type=LeaseSigningAuditEvent.EventType.SIGNATURE_COMMITTED,
                request=request,
                actor_role=role,
                metadata=meta,
            )
            session.refresh_from_db()
            if session.status == "completed":
                record_lease_sign_audit(
                    session,
                    event_type=LeaseSigningAuditEvent.EventType.SIGNING_SESSION_COMPLETED,
                    request=request,
                    actor_role=role,
                    metadata={"token_fp": token_fingerprint(token)},
                )
        except Exception:
            logger.exception("esign.audit.after_sign session_id=%s", session.pk)
        return Response(
            {
                "detail": "Signed successfully.",
                "session": LeaseSigningSessionSerializer(
                    session, context={"request": request}
                ).data,
            },
            status=status.HTTP_200_OK,
        )
