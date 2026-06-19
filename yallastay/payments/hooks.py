"""Run side effects once when a payment first becomes completed (stub + Stripe)."""

from __future__ import annotations

import logging

from emails.services import send_transactional_email
from notifications.services import notify_user

logger = logging.getLogger(__name__)


def on_payment_first_completed(payment) -> None:
    """
    Idempotent per payment row: team chat, e-sign session, payer receipt email,
    in-app payment notification.
    """
    try:
        from lifestyle_services.services import activate_subscription_after_payment

        activate_subscription_after_payment(payment)
    except Exception:
        logger.exception(
            "lifestyle.activate_subscription_after_payment failed payment_id=%s",
            payment.id,
        )

    from messaging.payment_messages import notify_realtor_rental_payment_received

    notify_realtor_rental_payment_received(payment)

    try:
        from esign.services import after_rental_payment_completed

        after_rental_payment_completed(payment)
    except Exception:
        logger.exception(
            "esign.after_rental_payment_completed failed payment_id=%s", payment.id
        )

    try:
        _send_payer_receipt_and_notification(payment)
    except Exception:
        logger.exception("payment receipt notify failed payment_id=%s", payment.id)


def _send_payer_receipt_and_notification(payment) -> None:
    if payment.status != "completed":
        return
    user = payment.user
    ptype = payment.get_payment_type_display()
    amount_s = f"{payment.amount} {payment.currency}".strip()
    subject = f"Payment received - {amount_s}"
    body = (
        f"Hi {(user.first_name or '').strip() or 'there'},\n\n"
        f"We’ve recorded your {ptype.lower()} payment of {amount_s}.\n\n"
        f"You can review it anytime in your dashboard.\n\n"
        f" -  Yallastay"
    )
    send_transactional_email(
        user.email,
        subject=subject,
        body_text=body,
        template_key="payment_receipt",
        user=user,
    )
    notify_user(
        user,
        "payment",
        subject,
        f"{ptype}: {amount_s}",
        link="/dashboard",
    )
    logger.info("payment.receipt.sent: payment_id=%s user_id=%s", payment.id, user.id)
