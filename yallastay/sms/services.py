"""
Outbound SMS - single entry point for other apps. Do not import Twilio outside this package.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from django.conf import settings

from core.template_render import render_template_string

from .models import SmsMessage

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

logger = logging.getLogger(__name__)


def _log_dev_outbound_sms(msg: SmsMessage) -> None:
    """When DEBUG is True, log SMS preview to the runserver / console."""
    if not getattr(settings, "DEBUG", False):
        return
    body = (msg.body or "")[:500]
    logger.info(
        "[OUTBOUND SMS] id=%s to=%s template_key=%s status=%s\n--- body ---\n%s",
        msg.id,
        msg.to_number,
        msg.template_key or "-",
        msg.status,
        body,
    )


def send_sms(
    to_number: str,
    *,
    body: str = "",
    template_key: str = "",
    user: AbstractUser | None = None,
) -> SmsMessage:
    """
    Queue/send an SMS and persist a row for audit.

    If ``TWILIO_ACCOUNT_SID`` / ``TWILIO_AUTH_TOKEN`` / ``TWILIO_FROM_NUMBER`` are not all set,
    the message is stored with status ``skipped`` (no provider call).
    """
    to_number = (to_number or "").strip()
    msg = SmsMessage.objects.create(
        to_number=to_number,
        body=body or "",
        template_key=template_key or "",
        user=user,
        status=SmsMessage.STATUS_QUEUED,
    )

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.environ.get("TWILIO_FROM_NUMBER", "").strip()

    if not all([account_sid, auth_token, from_number]):
        msg.status = SmsMessage.STATUS_SKIPPED
        msg.error_message = "Twilio env not configured (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER)"
        msg.save(update_fields=["status", "error_message", "updated_at"])
        logger.info("sms id=%s skipped: no Twilio configuration", msg.id)
        _log_dev_outbound_sms(msg)
        return msg

    try:
        from twilio.rest import Client  # type: ignore[import-untyped]
    except ImportError:
        msg.status = SmsMessage.STATUS_SKIPPED
        msg.error_message = "twilio package not installed (pip install twilio)"
        msg.save(update_fields=["status", "error_message", "updated_at"])
        logger.warning("sms id=%s skipped: twilio not installed", msg.id)
        _log_dev_outbound_sms(msg)
        return msg

    try:
        msg.status = SmsMessage.STATUS_SENDING
        msg.save(update_fields=["status", "updated_at"])

        client = Client(account_sid, auth_token)
        twilio_msg = client.messages.create(
            body=body or "",
            from_=from_number,
            to=to_number,
        )
        msg.provider_message_id = twilio_msg.sid
        msg.status = SmsMessage.STATUS_SENT
        msg.save(
            update_fields=[
                "provider_message_id",
                "status",
                "error_message",
                "updated_at",
            ]
        )
        logger.info("sms id=%s sent sid=%s", msg.id, twilio_msg.sid)
        _log_dev_outbound_sms(msg)
    except Exception as e:
        logger.exception("sms id=%s failed", msg.id)
        msg.status = SmsMessage.STATUS_FAILED
        msg.error_message = str(e)[:2000]
        msg.save(update_fields=["status", "error_message", "updated_at"])
        _log_dev_outbound_sms(msg)

    return msg


def send_sms_from_template(
    to_number: str,
    template_key: str,
    context: dict | None = None,
    *,
    user: AbstractUser | None = None,
) -> SmsMessage:
    """
    Load an active :class:`~sms.models.SmsTemplate` by ``template_key``,
    render ``body`` with ``context``, then send via :func:`send_sms`.
    """
    from .models import SmsTemplate

    context = context or {}
    t = SmsTemplate.objects.filter(key=template_key, is_active=True).first()
    if not t:
        raise ValueError(f"No active SMS template with key={template_key!r}")

    body = render_template_string(t.body, context)
    return send_sms(to_number, body=body, template_key=template_key, user=user)
