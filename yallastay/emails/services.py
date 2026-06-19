"""
Transactional email - single entry point for other apps.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from core.template_render import render_template_string

from .models import EmailMessage

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

logger = logging.getLogger(__name__)


def _log_dev_outbound_email(msg: EmailMessage) -> None:
    """When DEBUG is True, log full preview to the runserver / console (no secrets beyond message body)."""
    if not getattr(settings, "DEBUG", False):
        return
    preview = (msg.body_text or "")[:1200]
    logger.info(
        "[OUTBOUND EMAIL] id=%s to=%s template_key=%s status=%s subject=%r\n--- body_text ---\n%s",
        msg.id,
        msg.to_email,
        msg.template_key or "-",
        msg.status,
        (msg.subject or "")[:300],
        preview,
    )


def send_transactional_email(
    to_email: str,
    *,
    subject: str = "",
    body_text: str = "",
    body_html: str = "",
    template_key: str = "",
    user: AbstractUser | None = None,
) -> EmailMessage:
    """
    Persist a row and send via Django's email backend (SMTP, console, SendGrid API via Anymail, etc.).

    If ``DEFAULT_FROM_EMAIL`` is empty and no SMTP is usable, status is ``skipped``.
    """
    to_email = (to_email or "").strip()
    msg = EmailMessage.objects.create(
        to_email=to_email,
        subject=subject or "",
        body_text=body_text or "",
        body_html=body_html or "",
        template_key=template_key or "",
        user=user,
        status=EmailMessage.STATUS_QUEUED,
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or ""
    if not from_email or "@" not in from_email:
        msg.status = EmailMessage.STATUS_SKIPPED
        msg.error_message = "DEFAULT_FROM_EMAIL not configured"
        msg.save(update_fields=["status", "error_message", "updated_at"])
        logger.info("email id=%s skipped: DEFAULT_FROM_EMAIL", msg.id)
        _log_dev_outbound_email(msg)
        return msg

    try:
        msg.status = EmailMessage.STATUS_SENDING
        msg.save(update_fields=["status", "updated_at"])

        mail = EmailMultiAlternatives(
            subject=subject or "(no subject)",
            body=body_text or "",
            from_email=from_email,
            to=[to_email],
        )
        if body_html:
            mail.attach_alternative(body_html, "text/html")

        count = mail.send(fail_silently=False)
        if count:
            msg.status = EmailMessage.STATUS_SENT
            msg.provider_message_id = (
                os.environ.get("EMAIL_MOCK_PROVIDER_ID", "") or f"local-{msg.id}"
            )
        else:
            msg.status = EmailMessage.STATUS_FAILED
            msg.error_message = "mail.send() returned 0"
        msg.save(
            update_fields=[
                "status",
                "provider_message_id",
                "error_message",
                "updated_at",
            ]
        )
        logger.info("email id=%s status=%s", msg.id, msg.status)
        _log_dev_outbound_email(msg)
    except Exception as e:
        logger.exception("email id=%s failed", msg.id)
        msg.status = EmailMessage.STATUS_FAILED
        msg.error_message = str(e)[:2000]
        msg.save(update_fields=["status", "error_message", "updated_at"])
        _log_dev_outbound_email(msg)

    return msg


def send_transactional_email_from_template(
    to_email: str,
    template_key: str,
    context: dict | None = None,
    *,
    user: AbstractUser | None = None,
) -> EmailMessage:
    """
    Load an active :class:`~emails.models.EmailTemplate` by ``template_key``,
    render ``subject`` / ``body_text`` / ``body_html`` with ``context``, then send.

    Template strings use ``{placeholder}`` style; unknown keys become empty strings.
    """
    from .models import EmailTemplate

    context = context or {}
    t = EmailTemplate.objects.filter(key=template_key, is_active=True).first()
    if not t:
        raise ValueError(f"No active email template with key={template_key!r}")

    return send_transactional_email(
        to_email,
        subject=render_template_string(t.subject, context),
        body_text=render_template_string(t.body_text, context),
        body_html=render_template_string(t.body_html, context),
        template_key=template_key,
        user=user,
    )
