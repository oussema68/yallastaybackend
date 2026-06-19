"""Password reset email using Django's PasswordResetTokenGenerator + transactional template."""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from emails.services import send_transactional_email_from_template

logger = logging.getLogger(__name__)

password_reset_token_generator = PasswordResetTokenGenerator()


def build_password_reset_link(user) -> str:
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = password_reset_token_generator.make_token(user)
    base = (getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")
    query = urlencode({"uid": uidb64, "token": token})
    return f"{base}/reset-password?{query}"


def send_password_reset_email(user) -> None:
    if not user.is_active:
        return
    first = (user.first_name or "").strip() or "there"
    ctx = {
        "first_name": first,
        "email": user.email,
        "reset_link": build_password_reset_link(user),
    }
    try:
        send_transactional_email_from_template(
            user.email,
            "password_reset",
            ctx,
            user=user,
        )
    except ValueError as e:
        logger.warning("password_reset template missing: %s", e)
    except Exception:
        logger.exception("send_password_reset_email failed for user_id=%s", user.pk)
