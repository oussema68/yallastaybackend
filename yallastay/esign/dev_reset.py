"""Development-only reset for a lease signing session (see management command)."""

from __future__ import annotations

import logging
import secrets

from django.conf import settings
from django.db import models, transaction

logger = logging.getLogger(__name__)


def dev_reset_lease_signing_session(session_id: int):
    """
    Clear contract PDFs, signatures, audit trail, and signing progress for one session.
    Regenerates magic-link tokens. Optionally restores reservation/listing state if the
    lease was fully completed.

    Raises RuntimeError if :setting:`ESIGN_DEV_RESET_ENABLED` is false.
    """
    if not getattr(settings, "ESIGN_DEV_RESET_ENABLED", False):
        raise RuntimeError(
            "ESIGN_DEV_RESET_ENABLED is false - this reset is only allowed in development."
        )

    from esign.models import LeaseSigningAuditEvent, LeaseSigningSession

    with transaction.atomic():
        session = (
            LeaseSigningSession.objects.select_for_update()
            .select_related("reservation", "reservation__listing")
            .get(pk=session_id)
        )
        was_completed = session.status == "completed"

        LeaseSigningAuditEvent.objects.filter(session=session).delete()

        for field in session._meta.fields:
            if not isinstance(field, models.FileField):
                continue
            f = getattr(session, field.name)
            if f:
                f.delete(save=False)
            if field.null:
                setattr(session, field.name, None)
            else:
                setattr(session, field.name, "")

        session.renter_token = secrets.token_urlsafe(32)
        session.lister_token = secrets.token_urlsafe(32)
        session.status = "pending"
        session.renter_signed_at = None
        session.lister_signed_at = None
        session.signature_field_boxes = {}
        session.contract_pdf_sha256 = ""
        session.provider_metadata = {}

        session.save()

        reservation = session.reservation
        listing = reservation.listing

        if was_completed:
            if listing.leased:
                listing.leased = False
                listing.save(update_fields=["leased", "updated_at"])
            if reservation.status == "completed":
                reservation.status = "confirmed"
                reservation.save(update_fields=["status", "updated_at"])

        dld = dict(reservation.dld_metadata or {})
        if (
            dld.pop("lease_signed_at", None) is not None
            or dld.pop("lease_signing_session_id", None) is not None
        ):
            reservation.dld_metadata = dld
            reservation.save(update_fields=["dld_metadata", "updated_at"])

    session.refresh_from_db()
    if getattr(settings, "ESIGN_AUTO_GENERATE_CONTRACT_PDF", False):
        try:
            from esign.pdf_service import attach_contract_pdf_to_session

            attach_contract_pdf_to_session(session)
        except Exception:
            logger.exception(
                "esign.dev_reset.attach_contract_pdf_failed session_id=%s", session.pk
            )

    logger.warning(
        "esign.dev_reset: session_id=%s reservation_id=%s was_completed=%s",
        session.pk,
        session.reservation_id,
        was_completed,
    )
    return session
