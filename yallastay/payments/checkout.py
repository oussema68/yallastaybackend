"""Shared checkout response for stub and Stripe (used by payment initiate + lifestyle checkout)."""

from __future__ import annotations

import logging
import uuid

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def initiate_checkout_for_payment(payment, *, user_id: int | None = None) -> Response:
    """
    Build a 201 Response with checkout payload for an existing pending Payment row.
    Updates payment.transaction_id for Stripe; stub assigns a fake transaction id.
    """
    provider = getattr(settings, "PAYMENT_PROVIDER", "stub").lower()
    uid = user_id if user_id is not None else payment.user_id

    if provider == "stripe":
        from .stripe_service import create_checkout_session

        try:
            payload = create_checkout_session(payment)
        except RuntimeError as e:
            logger.warning(
                "payment.checkout.stripe.failed: user_id=%s error=%s",
                uid,
                e,
            )
            return Response(
                {"detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.exception(
                "payment.checkout.stripe.error: user_id=%s payment_id=%s",
                uid,
                payment.id,
            )
            return Response(
                {"detail": f"Stripe error: {e}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        logger.info(
            "payment.checkout.stripe: user_id=%s payment_id=%s reservation_id=%s",
            uid,
            payment.id,
            payment.reservation_id,
        )
        return Response(payload, status=status.HTTP_201_CREATED)

    payment.transaction_id = f"ys_{uuid.uuid4().hex[:16]}"
    payment.save(update_fields=["transaction_id"])
    token_prefix = settings.STUB_CHECKOUT_CLIENT_TOKEN_PREFIX
    logger.info(
        "payment.checkout.stub: user_id=%s payment_id=%s type=%s reservation_id=%s",
        uid,
        payment.id,
        payment.payment_type,
        payment.reservation_id,
    )
    return Response(
        {
            "payment_id": payment.id,
            "transaction_id": payment.transaction_id,
            "checkout_url": f"/checkout/stub/{payment.transaction_id}",
            "client_secret": f"{token_prefix}_{payment.transaction_id}",
            "provider": "stub",
            "message": "Stub checkout. Use PAYMENT_PROVIDER=stripe for Stripe, or POST to /api/payments/webhook/stub/ to simulate paid.",
        },
        status=status.HTTP_201_CREATED,
    )
