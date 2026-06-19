"""Lease signing orchestration: emails, in-app notifications, reservation metadata."""

from __future__ import annotations

import logging
import secrets
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Q
from django.utils import timezone

from emails.services import send_transactional_email
from notifications.services import notify_user

from .audit import (
    UAE_ELECTRONIC_CONSENT_SUMMARY,
    UAE_ELECTRONIC_CONSENT_VERSION,
    consent_required_for_request,
)
from .models import LeaseSigningSession
from .signing_slots import (
    count_lister_slots_saved,
    count_renter_slots_saved,
    norm_boxes,
    renter_placements_missing_for_lister_upload,
    role_rects_list,
)
from .frontend_urls import frontend_base_url
from .parties import lease_signing_lister_user
from .signature_utils import validate_signature_png

if TYPE_CHECKING:
    from payments.models import Payment

logger = logging.getLogger(__name__)


def session_has_contract_pdf(session: LeaseSigningSession) -> bool:
    return bool(session.lister_contract_pdf or session.contract_pdf)


def _frontend_sign_url(token: str) -> str:
    return f"{frontend_base_url()}/sign/lease/{token}"


def _send_invite_emails_and_notifications(session: LeaseSigningSession) -> None:
    reservation = session.reservation
    listing = reservation.listing
    renter = reservation.user
    signer = lease_signing_lister_user(listing)
    title = (listing.title or "Your rental")[:200]

    renter_link = _frontend_sign_url(session.renter_token)
    lister_link = _frontend_sign_url(session.lister_token)

    send_transactional_email(
        renter.email,
        subject=f"Lease signing - {title}",
        body_text=(
            f"Hi {(renter.first_name or '').strip() or 'there'},\n\n"
            f"Your payment is recorded for “{title}”. "
            f"The landlord side will upload the tenancy agreement PDF; "
            f"then you can review and sign using your link (keep private):\n{renter_link}\n\n"
            f" -  Yallastay"
        ),
        template_key="lease_sign_invite_renter",
        user=renter,
    )
    send_transactional_email(
        signer.email,
        subject=f"Upload lease PDF - {title}",
        body_text=(
            f"Hi {(signer.first_name or '').strip() or 'there'},\n\n"
            f"The renter has completed a rental payment for “{title}”. "
            f"Upload the tenancy agreement PDF from your Yallastay dashboard "
            f"(Lease agreements & signatures) before they can sign. "
            f"After upload, both parties use their signing links:\n{lister_link}\n\n"
            f" -  Yallastay"
        ),
        template_key="lease_sign_invite_lister",
        user=signer,
    )

    notify_user(
        renter,
        "esign",
        "Lease signing started",
        f"Wait for the lease PDF for “{title}”, then open your signing link from email or dashboard.",
        link="/dashboard",
    )
    notify_user(
        signer,
        "esign",
        "Upload lease PDF",
        f"Upload the tenancy PDF for “{title}” from your dashboard, then sign when it’s your turn.",
        link="/dashboard",
    )
    if listing.listed_by_id != signer.id:
        notify_user(
            listing.listed_by,
            "esign",
            "Lease signing started",
            f"A renter paid for “{title}”. The property owner was notified to upload and sign the lease.",
            link="/dashboard",
        )

    logger.info(
        "esign.invites.sent: session_id=%s reservation_id=%s",
        session.id,
        reservation.id,
    )


def _notify_completion(session: LeaseSigningSession) -> None:
    reservation = session.reservation
    listing = reservation.listing
    renter = reservation.user
    signer = lease_signing_lister_user(listing)
    title = (listing.title or "Your rental")[:200]

    send_transactional_email(
        renter.email,
        subject=f"Lease signed - {title}",
        body_text=(
            f"Both parties have signed the tenancy agreement for “{title}”.\n\n"
            f"Next: coordinate Ejari / handover with the other party in Messages.\n\n"
            f" -  Yallastay"
        ),
        template_key="lease_sign_completed",
        user=renter,
    )
    send_transactional_email(
        signer.email,
        subject=f"Lease signed - {title}",
        body_text=(
            f"The tenancy agreement for “{title}” is fully signed.\n\n" f" -  Yallastay"
        ),
        template_key="lease_sign_completed",
        user=signer,
    )
    notify_user(
        renter,
        "contract",
        "Lease fully signed",
        f"“{title}” - all signatures collected.",
        link="/messages",
    )
    notify_user(
        signer,
        "contract",
        "Lease fully signed",
        f"“{title}” - all signatures collected.",
        link="/messages",
    )
    if listing.listed_by_id != signer.id:
        notify_user(
            listing.listed_by,
            "contract",
            "Lease fully signed",
            f"“{title}” - the renter and property owner have completed signatures.",
            link="/messages",
        )
    logger.info(
        "esign.completed: session_id=%s reservation_id=%s",
        session.id,
        reservation.id,
    )


def after_rental_payment_completed(payment: Payment) -> LeaseSigningSession | None:
    """
    After rent/deposit clears for a reservation, start a lease signing session
    (one per reservation). Idempotent if a session already exists.
    """
    if payment.status != "completed":
        logger.info(
            "esign.after_payment.skip: payment_id=%s reason=not_completed",
            payment.id,
        )
        return None
    if payment.payment_type not in ("rent", "deposit"):
        return None
    if not payment.reservation_id:
        return None

    reservation = payment.reservation
    if LeaseSigningSession.objects.filter(reservation=reservation).exists():
        logger.info(
            "esign.after_payment.skip: reservation_id=%s reason=session_exists",
            reservation.id,
        )
        return None

    renter_token = secrets.token_urlsafe(32)
    lister_token = secrets.token_urlsafe(32)
    session = LeaseSigningSession.objects.create(
        reservation=reservation,
        triggering_payment=payment,
        renter_token=renter_token,
        lister_token=lister_token,
        status="pending",
    )
    if getattr(settings, "ESIGN_AUTO_GENERATE_CONTRACT_PDF", False):
        try:
            from esign.pdf_service import attach_contract_pdf_to_session

            attach_contract_pdf_to_session(session)
        except Exception:
            logger.exception(
                "esign.attach_contract_pdf_failed session_id=%s", session.id
            )
    _send_invite_emails_and_notifications(session)
    logger.info(
        "esign.session.created: session_id=%s payment_id=%s reservation_id=%s",
        session.id,
        payment.id,
        reservation.id,
    )
    return session


def preview_sign_token(token: str) -> tuple[dict | None, str | None]:
    """
    Public preview for magic-link page (GET). Renter must sign before lister (product rule).
    """
    token = (token or "").strip()
    if not token:
        return None, "not_found"

    session = (
        LeaseSigningSession.objects.filter(
            Q(renter_token=token) | Q(lister_token=token)
        )
        .select_related("reservation", "reservation__listing")
        .first()
    )
    if not session:
        return None, "not_found"
    if session.status == "cancelled":
        return None, "cancelled"

    listing = session.reservation.listing
    title = (listing.title or "This property").strip()
    is_renter = session.renter_token == token
    role = "renter" if is_renter else "lister"

    if session.status == "completed":
        return (
            {
                "listing_title": title,
                "your_role": role,
                "can_sign": False,
                "status": session.status,
                "renter_signed": True,
                "lister_signed": True,
                "message": "This lease is already fully signed.",
                "pdf_url": f"/esign/sign/{token}/pdf/",
                "pdf_available": session_has_contract_pdf(session),
                "electronic_consent": {
                    "version": UAE_ELECTRONIC_CONSENT_VERSION,
                    "summary": UAE_ELECTRONIC_CONSENT_SUMMARY,
                },
                "electronic_consent_required": False,
            },
            None,
        )

    has_pdf = session_has_contract_pdf(session)

    norm = norm_boxes(session)
    renter_rects = role_rects_list(norm, "renter")
    lister_rects = role_rects_list(norm, "lister")
    missing_renter_placements = renter_placements_missing_for_lister_upload(session)

    if is_renter:
        can_sign = (
            not session.renter_signed_at and has_pdf and not missing_renter_placements
        )
        msg = None
        if session.renter_signed_at:
            msg = "You’ve already signed. Waiting for the landlord to sign."
        elif not has_pdf:
            msg = "Waiting for the lease PDF to be uploaded. Check back soon or use your dashboard."
        elif missing_renter_placements:
            msg = (
                "Signature fields must be placed on the lease PDF "
                "before you can sign. Check back soon."
            )
    else:
        # Lister: cannot sign until renter has signed
        can_sign = bool(
            session.renter_signed_at and not session.lister_signed_at and has_pdf
        )
        msg = None
        if not has_pdf:
            msg = "Upload the tenancy agreement PDF from your Yallastay dashboard (Lease agreements & signatures), then the renter can sign."
        elif not session.renter_signed_at:
            msg = (
                "The renter must sign first. You’ll get an email when they’ve signed; "
                "then return here to countersign."
            )
        elif session.lister_signed_at:
            msg = "You’ve already signed this lease."
    multi_renter = len(renter_rects) > 1
    multi_lister = len(lister_rects) > 1

    placement_rects: list[dict[str, Any]] = []
    signature_slots_total = 1
    signature_slots_completed = 0
    current_slot_index: int | None = None

    if is_renter:
        placement_rects = renter_rects
        signature_slots_total = max(1, len(renter_rects))
        signature_slots_completed = count_renter_slots_saved(session)
        if multi_renter and not session.renter_signed_at:
            current_slot_index = signature_slots_completed
    else:
        placement_rects = lister_rects
        signature_slots_total = max(1, len(lister_rects))
        signature_slots_completed = count_lister_slots_saved(session)
        if multi_lister and not session.lister_signed_at:
            current_slot_index = signature_slots_completed

    payload = {
        "listing_title": title,
        "your_role": role,
        "can_sign": can_sign,
        "status": session.status,
        "renter_signed": bool(session.renter_signed_at),
        "lister_signed": bool(session.lister_signed_at),
        "message": msg,
        "pdf_url": f"/esign/sign/{token}/pdf/",
        "pdf_available": has_pdf,
        "multi_slot_signing": (is_renter and multi_renter)
        or ((not is_renter) and multi_lister),
        "placement_rects": placement_rects,
        "signature_slots_total": signature_slots_total,
        "signature_slots_completed": signature_slots_completed,
        "current_slot_index": current_slot_index,
        "electronic_consent": {
            "version": UAE_ELECTRONIC_CONSENT_VERSION,
            "summary": UAE_ELECTRONIC_CONSENT_SUMMARY,
        },
        "electronic_consent_required": consent_required_for_request(
            session, token, role
        ),
    }
    return (payload, None)


def sign_with_token(
    token: str,
    *,
    signature_png_bytes: bytes | None = None,
    signature_slot_index: int | None = None,
) -> tuple[LeaseSigningSession | None, str | None]:
    """
    Mark renter or lister as signed; stores PNG(s) of drawn signatures.
    Multi-placement leases: pass signature_slot_index 0..n-1 per POST, in order.
    Returns (session, error_code).
    error_code: not_found | already_done | cancelled | renter_must_sign_first |
    missing_signature | signature_too_small | signature_too_large |
    invalid_signature_format | invalid_signature_dimensions |
    missing_slot_index | invalid_slot_index | slot_order |
    missing_signature_placements
    """
    token = (token or "").strip()
    if not token:
        return None, "not_found"

    session = (
        LeaseSigningSession.objects.filter(
            Q(renter_token=token) | Q(lister_token=token)
        )
        .select_related("reservation", "reservation__listing", "reservation__user")
        .first()
    )

    if not session:
        return None, "not_found"
    if session.status == "cancelled":
        return session, "cancelled"
    if session.status == "completed":
        return session, "already_done"

    if not session_has_contract_pdf(session):
        return None, "no_contract_pdf"

    now = timezone.now()
    norm = norm_boxes(session)

    if session.renter_token == token:
        if session.renter_signed_at:
            return session, "already_done"
        if renter_placements_missing_for_lister_upload(session):
            return None, "missing_signature_placements"
        renter_rects = role_rects_list(norm, "renter")
        multi = len(renter_rects) > 1

        if multi:
            if signature_slot_index is None:
                return None, "missing_slot_index"
            try:
                slot_idx = int(signature_slot_index)
            except (TypeError, ValueError):
                return None, "invalid_slot_index"
            if slot_idx < 0 or slot_idx >= len(renter_rects):
                return None, "invalid_slot_index"
            filled = count_renter_slots_saved(session)
            if slot_idx != filled:
                return None, "slot_order"
            sig_err = validate_signature_png(signature_png_bytes)
            if sig_err:
                return None, sig_err
            fname = f"renter-sig-{session.pk}-s{slot_idx + 1}.png"
            field = getattr(session, f"renter_signature_slot_{slot_idx + 1}")
            field.save(fname, ContentFile(signature_png_bytes), save=False)
            uf = [f"renter_signature_slot_{slot_idx + 1}", "updated_at"]
            if filled + 1 >= len(renter_rects):
                session.renter_signed_at = now
                uf.append("renter_signed_at")
            session.save(update_fields=uf)
        else:
            sig_err = validate_signature_png(signature_png_bytes)
            if sig_err:
                return None, sig_err
            session.renter_signed_at = now
            session.renter_signature_image.save(
                f"renter-sig-{session.pk}.png",
                ContentFile(signature_png_bytes),
                save=False,
            )
            session.save(
                update_fields=[
                    "renter_signed_at",
                    "renter_signature_image",
                    "updated_at",
                ]
            )
    elif session.lister_token == token:
        if session.lister_signed_at:
            return session, "already_done"
        if not session.renter_signed_at:
            return session, "renter_must_sign_first"
        lister_rects = role_rects_list(norm, "lister")
        multi = len(lister_rects) > 1

        if multi:
            if signature_slot_index is None:
                return None, "missing_slot_index"
            try:
                slot_idx = int(signature_slot_index)
            except (TypeError, ValueError):
                return None, "invalid_slot_index"
            if slot_idx < 0 or slot_idx >= len(lister_rects):
                return None, "invalid_slot_index"
            filled = count_lister_slots_saved(session)
            if slot_idx != filled:
                return None, "slot_order"
            sig_err = validate_signature_png(signature_png_bytes)
            if sig_err:
                return None, sig_err
            fname = f"lister-sig-{session.pk}-s{slot_idx + 1}.png"
            field = getattr(session, f"lister_signature_slot_{slot_idx + 1}")
            field.save(fname, ContentFile(signature_png_bytes), save=False)
            uf = [f"lister_signature_slot_{slot_idx + 1}", "updated_at"]
            if filled + 1 >= len(lister_rects):
                session.lister_signed_at = now
                uf.append("lister_signed_at")
            session.save(update_fields=uf)
        else:
            sig_err = validate_signature_png(signature_png_bytes)
            if sig_err:
                return None, sig_err
            session.lister_signed_at = now
            session.lister_signature_image.save(
                f"lister-sig-{session.pk}.png",
                ContentFile(signature_png_bytes),
                save=False,
            )
            session.save(
                update_fields=[
                    "lister_signed_at",
                    "lister_signature_image",
                    "updated_at",
                ]
            )
    else:
        return None, "not_found"

    session.refresh_from_db()
    try:
        from esign.pdf_service import rebuild_signed_pdf

        rebuild_signed_pdf(session)
    except Exception:
        logger.exception("esign.rebuild_signed_pdf failed session_id=%s", session.id)

    session.refresh_from_db()
    if session.renter_signed_at and session.lister_signed_at:
        session.status = "completed"
        session.save(update_fields=["status", "updated_at"])
        reservation = session.reservation
        dld = dict(reservation.dld_metadata or {})
        dld["lease_signed_at"] = now.isoformat()
        dld["lease_signing_session_id"] = session.id
        reservation.dld_metadata = dld
        reservation.save(update_fields=["dld_metadata", "updated_at"])
        listing = reservation.listing
        if not listing.leased:
            listing.leased = True
            listing.save(update_fields=["leased", "updated_at"])
        if reservation.status != "completed":
            reservation.status = "completed"
            reservation.save(update_fields=["status", "updated_at"])
        _notify_completion(session)

    logger.info(
        "esign.sign: session_id=%s status=%s renter_signed=%s lister_signed=%s",
        session.id,
        session.status,
        bool(session.renter_signed_at),
        bool(session.lister_signed_at),
    )
    return session, None
