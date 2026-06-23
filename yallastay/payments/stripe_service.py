"""
Stripe Checkout Session creation and webhook handling.

Used only when PAYMENT_PROVIDER=stripe. Stub flow stays in views (no Stripe import).
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from core.db_rls import set_request_user_id_for_rls
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def _amount_to_stripe_unit(amount: Decimal, currency: str) -> int:
    """Stripe amounts are in the smallest currency unit (e.g. AED: fils, 2 decimals)."""
    return int((amount * 100).quantize(Decimal("1")))


def create_checkout_session(payment) -> dict:
    """
    Create a Stripe Checkout Session for this Payment row.
    Updates payment.transaction_id to session id and returns payload for the API response.
    """
    import stripe

    if not getattr(settings, "STRIPE_SECRET_KEY", ""):
        raise RuntimeError(
            "STRIPE_SECRET_KEY is not set. Configure it when using PAYMENT_PROVIDER=stripe."
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY
    currency = (payment.currency or "aed").lower()
    base = settings.FRONTEND_URL.rstrip("/")

    label = f"Yallastay - {payment.get_payment_type_display()}"
    if payment.reservation_id and payment.reservation:
        label = f"{label} ({payment.reservation.listing.title})"

    # Hosted Checkout: Apple Pay / Google Pay appear when enabled in the Stripe Dashboard for this account
    # and (for Apple Pay) the domain is verified under Settings → Payment methods. No extra API flags for
    # "Huawei Pay" is not listed; Stripe exposes Apple Pay, Google Pay, and cards on Checkout as configured.
    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        payment_method_options={
            "card": {"request_three_d_secure": "automatic"},
        },
        line_items=[
            {
                "price_data": {
                    "currency": currency,
                    "unit_amount": _amount_to_stripe_unit(payment.amount, currency),
                    "product_data": {"name": label[:120]},
                },
                "quantity": 1,
            }
        ],
        success_url=f"{base}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base}/payment/cancel",
        client_reference_id=str(payment.id),
        metadata={
            "payment_id": str(payment.id),
            "payment_type": payment.payment_type,
            **(
                {"lifestyle_subscription_id": str(payment.lifestyle_subscription_id)}
                if payment.lifestyle_subscription_id
                else {}
            ),
        },
    )

    payment.transaction_id = session.id
    payment.save(update_fields=["transaction_id"])

    logger.info(
        "stripe.checkout.created: payment_id=%s session_id=%s amount=%s",
        payment.id,
        session.id,
        payment.amount,
    )

    return {
        "payment_id": payment.id,
        "transaction_id": session.id,
        "checkout_url": session.url,
        "client_secret": None,
        "stripe_session_id": session.id,
        "publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", "") or None,
        "provider": "stripe",
    }


def resolve_checkout_payment_method_label(session_obj: dict) -> str:
    """
    Derive a short label for how the customer paid (Apple Pay, Google Pay, card brand, link, etc.).
    Uses the Checkout Session's PaymentIntent - must run with stripe.api_key set.
    """
    import stripe

    pi_id = session_obj.get("payment_intent")
    if not pi_id:
        return ""

    try:
        pi = stripe.PaymentIntent.retrieve(
            str(pi_id),
            expand=["payment_method"],
        )
    except Exception as e:
        logger.warning(
            "stripe.payment_intent.retrieve failed session=%s err=%s",
            session_obj.get("id"),
            e,
        )
        return ""

    pm = pi.get("payment_method")
    if isinstance(pm, str):
        try:
            pm = stripe.PaymentMethod.retrieve(pm)
        except Exception as e:
            logger.warning("stripe.payment_method.retrieve failed err=%s", e)
            return ""
    if not pm or not isinstance(pm, dict):
        return ""

    ptype = (pm.get("type") or "").strip()
    if ptype == "card":
        card = pm.get("card") or {}
        wallet = card.get("wallet") or {}
        wtype = wallet.get("type") if isinstance(wallet, dict) else None
        if wtype in ("apple_pay", "google_pay", "samsung_pay"):
            return wtype
        brand = (card.get("brand") or "").strip().lower()
        if brand:
            return f"card_{brand}"[:50]
        return "card"
    if ptype:
        return ptype[:50]
    return ""


def _resolve_payment_from_session(session_obj: dict):
    from .models import Payment

    meta = session_obj.get("metadata") or {}
    pid = meta.get("payment_id") or session_obj.get("client_reference_id")
    if pid:
        try:
            return (
                Payment.objects.filter(pk=int(pid))
                .select_related("reservation", "reservation__listing", "user")
                .first()
            )
        except (TypeError, ValueError):
            pass

    sid = session_obj.get("id")
    if sid:
        return (
            Payment.objects.filter(transaction_id=sid)
            .select_related("reservation", "reservation__listing", "user")
            .first()
        )
    return None


def handle_stripe_webhook(request):
    """
    Verify Stripe signature, complete Payment on checkout.session.completed, notify realtor.
    Expects raw request.body (bytes) for signature verification.
    """
    import stripe

    if getattr(settings, "STRIPE_SECRET_KEY", ""):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    if not getattr(settings, "STRIPE_WEBHOOK_SECRET", ""):
        return Response(
            {"detail": "STRIPE_WEBHOOK_SECRET is not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    if not sig_header:
        return Response(
            {"detail": "Missing Stripe-Signature header."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload = request.body
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return Response(
            {"detail": "Invalid payload."}, status=status.HTTP_400_BAD_REQUEST
        )
    except stripe.error.SignatureVerificationError:
        return Response(
            {"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST
        )

    if event["type"] != "checkout.session.completed":
        return Response({"received": True, "type": event.get("type")}, status=200)

    session_obj = event["data"]["object"]
    if session_obj.get("payment_status") != "paid":
        logger.info(
            "checkout.session.completed but payment_status=%s session=%s",
            session_obj.get("payment_status"),
            session_obj.get("id"),
        )
        return Response({"received": True, "ignored": "not paid"}, status=200)

    payment = _resolve_payment_from_session(session_obj)
    if not payment:
        logger.warning("No Payment row for Stripe session id=%s", session_obj.get("id"))
        return Response({"received": True, "note": "no matching payment"}, status=200)

    method_label = resolve_checkout_payment_method_label(session_obj)
    hook_payment_id = None
    from .models import Payment

    # Lock so concurrent/retried webhook deliveries stay idempotent.
    with transaction.atomic():
        payment = (
            Payment.objects.select_for_update()
            .filter(pk=payment.pk)
            .select_related("reservation", "reservation__listing", "user")
            .first()
        )
        if not payment:
            logger.warning(
                "Stripe payment row disappeared after resolve: session=%s",
                session_obj.get("id"),
            )
            return Response(
                {"received": True, "note": "no matching payment"}, status=200
            )

        set_request_user_id_for_rls(payment.user_id)

        was_completed = payment.status == "completed"
        if not was_completed:
            payment.status = "completed"
            if method_label:
                payment.payment_method = method_label
            update_fields = ["status"]
            if method_label:
                update_fields.append("payment_method")
            payment.save(update_fields=update_fields)
            hook_payment_id = payment.id
    logger.info(
        "stripe.webhook.completed: payment_id=%s session_id=%s was_completed=%s",
        payment.id,
        session_obj.get("id"),
        was_completed,
    )

    if hook_payment_id:
        from payments.hooks import on_payment_first_completed

        payment_for_hook = (
            Payment.objects.filter(pk=hook_payment_id)
            .select_related("reservation", "reservation__listing", "user")
            .first()
        )
        if payment_for_hook:
            on_payment_first_completed(payment_for_hook)

    return Response({"received": True, "payment_id": payment.id}, status=200)
