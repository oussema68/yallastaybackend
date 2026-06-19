"""Send transactional email with link to verify address (uses emails app + BACKEND_URL)."""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from emails.services import send_transactional_email_from_template

from .tokens import email_verification_token_generator

logger = logging.getLogger(__name__)


def build_verification_link(user) -> str:
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token_generator.make_token(user)
    base = (getattr(settings, "BACKEND_URL", "") or "").rstrip("/")
    # Query-string form avoids broken links when tokens contain ``=`` (email clients / path encoding).
    query = urlencode({"uid": uidb64, "token": token, "redirect": "1"})
    return f"{base}/api/auth/verify-email/?{query}"


def send_email_verification(user) -> None:
    """
    Queue verification email. No-op if already verified or template missing.
    Failures are logged; callers should not block registration on email errors.
    """
    try:
        profile = user.profile
    except Exception:
        logger.warning("send_email_verification: user %s has no profile", user.pk)
        return
    if profile.is_email_verified:
        return
    first = (user.first_name or "").strip() or "there"
    ctx = {
        "first_name": first,
        "email": user.email,
        "verification_link": build_verification_link(user),
    }
    try:
        send_transactional_email_from_template(
            user.email,
            "email_verification",
            ctx,
            user=user,
        )
    except ValueError as e:
        logger.warning("email_verification template missing: %s", e)
    except Exception:
        logger.exception("send_email_verification failed for user_id=%s", user.pk)
