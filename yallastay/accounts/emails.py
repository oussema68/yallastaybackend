"""Transactional emails for account / realtor lifecycle."""

from __future__ import annotations

import logging

from django.conf import settings

from emails.services import send_transactional_email_from_template

logger = logging.getLogger(__name__)


def send_uae_id_submitted_emails(user, *, has_document: bool) -> None:
    """
    Notify the user (acknowledgment) and the verification team (internal) after UAE ID submission.
    Does not raise on failure (logs instead). Team email uses ``VERIFICATION_TEAM_EMAIL`` (same as document uploads).
    """
    first = (getattr(user, "first_name", None) or "").strip() or "there"
    base = (getattr(settings, "FRONTEND_URL", None) or "").rstrip("/")
    verify_url = f"{base}/verify" if base else "/verify"
    backend = (getattr(settings, "BACKEND_URL", None) or "").rstrip("/")
    admin_uae_list_url = (
        f"{backend}/admin/accounts/uaeidverification/" if backend else ""
    )
    if has_document:
        document_note = "We received an uploaded file with your Emirates ID number."
    else:
        document_note = (
            "No file was attached; you submitted your Emirates ID number only. "
            "We may ask for a scan if needed."
        )

    ctx_user = {
        "first_name": first,
        "user_email": user.email,
        "verify_url": verify_url,
        "document_note": document_note,
    }
    try:
        send_transactional_email_from_template(
            user.email,
            "uae_id_submitted_user",
            ctx_user,
            user=user,
        )
    except ValueError as e:
        logger.warning("uae_id_submitted_user template: %s", e)
    except Exception:
        logger.exception("uae_id_submitted_user failed user_id=%s", user.pk)

    team_email = (getattr(settings, "VERIFICATION_TEAM_EMAIL", None) or "").strip()
    if not team_email or "@" not in team_email:
        logger.warning(
            "VERIFICATION_TEAM_EMAIL is not set or invalid - skipping UAE ID team email "
            "(set VERIFICATION_TEAM_EMAIL in .env). user_id=%s",
            user.pk,
        )
        return

    ctx_team = {
        "first_name": first,
        "user_email": user.email,
        "user_id": str(user.pk),
        "document_note": document_note,
        "admin_uae_list_url": admin_uae_list_url
        or "(configure BACKEND_URL for admin link)",
    }
    try:
        send_transactional_email_from_template(
            team_email,
            "uae_id_submitted_team",
            ctx_team,
            user=user,
        )
    except ValueError as e:
        logger.warning("uae_id_submitted_team template: %s", e)
    except Exception:
        logger.exception("uae_id_submitted_team failed user_id=%s", user.pk)


def send_uae_id_approved_email(user) -> None:
    """
    Notify a renter that their Emirates ID verification was approved (admin action or model save).
    Does not raise on failure (logs instead).
    """
    first = (getattr(user, "first_name", None) or "").strip() or "there"
    base = (getattr(settings, "FRONTEND_URL", None) or "").rstrip("/")
    dashboard_url = f"{base}/dashboard" if base else "/dashboard"
    ctx = {
        "first_name": first,
        "user_email": user.email,
        "dashboard_url": dashboard_url,
    }
    try:
        send_transactional_email_from_template(
            user.email,
            "uae_id_approved_user",
            ctx,
            user=user,
        )
    except ValueError as e:
        logger.warning("uae_id_approved_user template: %s", e)
    except Exception:
        logger.exception("uae_id_approved_user failed user_id=%s", user.pk)


def send_landlord_approved_email(user, landlord_profile) -> None:
    """
    Notify a landlord that their owner account has been approved (admin action).
    Does not raise on failure (logs instead).
    """
    first = (getattr(user, "first_name", None) or "").strip() or "there"
    base = (getattr(settings, "FRONTEND_URL", None) or "").rstrip("/")
    dashboard_url = f"{base}/dashboard" if base else "/dashboard"
    ctx = {
        "first_name": first,
        "company_name": getattr(landlord_profile, "company_name", None) or "",
        "dashboard_url": dashboard_url,
    }
    try:
        send_transactional_email_from_template(
            user.email,
            "landlord_approved_user",
            ctx,
            user=user,
        )
    except ValueError as e:
        logger.warning("landlord_approved_user template: %s", e)
    except Exception:
        logger.exception("landlord_approved_user failed user_id=%s", user.pk)


def send_realtor_approved_email(user, realtor_profile) -> None:
    """
    Notify a realtor that their brokerage account has been approved.
    Does not raise on failure (logs instead).
    """
    first = (getattr(user, "first_name", None) or "").strip() or "there"
    base = (getattr(settings, "FRONTEND_URL", None) or "").rstrip("/")
    dashboard_url = f"{base}/my-listings" if base else "/my-listings"
    ctx = {
        "first_name": first,
        "agency_name": getattr(realtor_profile, "agency_name", None) or "",
        "dashboard_url": dashboard_url,
    }
    try:
        send_transactional_email_from_template(
            user.email,
            "realtor_approved_user",
            ctx,
            user=user,
        )
    except ValueError as e:
        logger.warning("realtor_approved_user template: %s", e)
    except Exception:
        logger.exception("realtor_approved_user failed user_id=%s", user.pk)
