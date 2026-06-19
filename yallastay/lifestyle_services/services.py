"""Side effects for lifestyle subscriptions (payment activation)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def activate_subscription_after_payment(payment) -> None:
    """
    When a lifestyle Payment completes, move the linked subscription from
    pending_payment to active. Idempotent if already active.
    """
    if payment.payment_type != "lifestyle" or not payment.lifestyle_subscription_id:
        return
    if payment.status != "completed":
        return

    sub = payment.lifestyle_subscription
    if sub is None:
        return
    if sub.user_id != payment.user_id:
        logger.warning(
            "lifestyle.activate.skip: payment user mismatch payment_id=%s sub_id=%s",
            payment.id,
            sub.id,
        )
        return
    if sub.status != "pending_payment":
        return

    sub.status = "active"
    sub.save(update_fields=["status", "updated_at"])
    logger.info(
        "lifestyle.subscription.activated: subscription_id=%s payment_id=%s",
        sub.id,
        payment.id,
    )


def cancel_pending_subscription_payment(subscription) -> None:
    """Mark pending Payment rows cancelled when the renter cancels before paying."""
    from payments.models import Payment

    if subscription.status != "pending_payment":
        return
    updated = Payment.objects.filter(
        lifestyle_subscription=subscription,
        status="pending",
    ).update(status="cancelled")
    if updated:
        logger.info(
            "lifestyle.subscription.cancelled_pending_payments: subscription_id=%s count=%s",
            subscription.id,
            updated,
        )
