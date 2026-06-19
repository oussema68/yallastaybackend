"""Transactional emails after document upload (user + verification team)."""

from __future__ import annotations

import logging

from django.conf import settings

from emails.services import send_transactional_email_from_template

from .checklist import (
    document_type_label,
    present_and_missing,
    profile_role,
    ROLE_LABEL,
)

logger = logging.getLogger(__name__)


def _lines_for_types(types: list[str]) -> str:
    if not types:
        return "(none)"
    return "\n".join(f"  • {document_type_label(t)}" for t in types)


def send_document_upload_emails(
    user,
    document,
    *,
    batch_type_keys: list[str] | None = None,
) -> None:
    """
    Notify verification team (internal) and the user (acknowledgment).
    Safe to call after upload; failures are logged and do not raise.

    For batch uploads, pass ``batch_type_keys`` with every ``document_type`` in that
    submission so the email summarizes the whole batch (one notification per batch).
    """
    role = profile_role(user)
    role_label = ROLE_LABEL.get(role or "", role or "Unknown")
    present, missing, _checklist = present_and_missing(user)

    if batch_type_keys:
        labels = [document_type_label(t) for t in batch_type_keys]
        latest_label = f"{len(batch_type_keys)} file(s): " + ", ".join(labels)
    else:
        latest_label = document_type_label(document.document_type)

    first = (getattr(user, "first_name", None) or "").strip() or "there"
    team_email = (getattr(settings, "VERIFICATION_TEAM_EMAIL", None) or "").strip()

    ctx_common = {
        "first_name": first,
        "user_email": user.email,
        "role_label": role_label,
        "latest_document_label": latest_label,
        "present_list": _lines_for_types(present),
        "missing_list": _lines_for_types(missing),
        "present_count": str(len(present)),
        "missing_count": str(len(missing)),
    }

    try:
        send_transactional_email_from_template(
            user.email,
            "documents_received_user",
            ctx_common,
            user=user,
        )
    except ValueError as e:
        logger.warning("documents_received_user template: %s", e)
    except Exception:
        logger.exception("documents_received_user failed user_id=%s", user.pk)

    if not team_email or "@" not in team_email:
        logger.warning(
            "VERIFICATION_TEAM_EMAIL is not set or invalid - skipping internal team email "
            "(set VERIFICATION_TEAM_EMAIL in .env to receive document checklist notifications). "
            "user_id=%s",
            user.pk,
        )
        return

    if batch_type_keys:
        internal_note = (
            f"Batch upload of {len(batch_type_keys)} file(s) in one submission. "
            f"Types: {', '.join(document_type_label(t) for t in batch_type_keys)}."
        )
    else:
        internal_note = f"Latest upload: {latest_label} (file on record)."

    ctx_team = {
        **ctx_common,
        "internal_note": internal_note,
    }
    try:
        send_transactional_email_from_template(
            team_email,
            "documents_submitted_team",
            ctx_team,
            user=user,
        )
    except ValueError as e:
        logger.warning("documents_submitted_team template: %s", e)
    except Exception:
        logger.exception("documents_submitted_team failed user_id=%s", user.pk)
