import logging

from core.db_rls import set_request_user_id_for_rls
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from rest_framework_simplejwt.authentication import JWTAuthentication

from .checkout import initiate_checkout_for_payment
from .models import Payment
from .serializers import PaymentSerializer, PaymentInitiateSerializer
from .stub_webhook import may_complete_stub_webhook

logger = logging.getLogger(__name__)


class PaymentListView(APIView):
    """GET: List current user's payments."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = Payment.objects.filter(user=request.user).order_by("-created_at")
        serializer = PaymentSerializer(payments, many=True)
        logger.info(
            "payment.list: user_id=%s count=%s",
            request.user.id,
            len(serializer.data),
        )
        return Response(serializer.data)


class PaymentInitiateView(APIView):
    """
    POST: Initiate payment.

    - PAYMENT_PROVIDER=stub (default): fake checkout URL for local testing.
    - PAYMENT_PROVIDER=stripe: real Stripe Checkout Session (requires STRIPE_SECRET_KEY).
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment_initiate"

    def post(self, request):
        serializer = PaymentInitiateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        payment = Payment.objects.create(
            user=request.user,
            amount=data["amount"],
            currency=data.get("currency", "AED"),
            payment_type=data["payment_type"],
            status="pending",
            transaction_id="",
            reservation=data.get("reservation_id"),
        )
        return initiate_checkout_for_payment(payment, user_id=request.user.id)


class PaymentWebhookStubView(APIView):
    """
    POST: Dev/test webhook - marks payment completed by transaction_id (no Stripe signature).

    **Authorization (non-test):** the caller must be the **payment owner** (JWT), or send
    ``X-Stub-Webhook-Secret`` matching ``STUB_WEBHOOK_SECRET``. In production (``DEBUG=False``)
    without a configured secret, only the payment owner or secret header may complete.

    Use ``/api/payments/webhook/stub/`` explicitly, or ``/api/payments/webhook/`` (alias).
    """

    permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "stub_webhook"

    def post(self, request):
        transaction_id = request.data.get("transaction_id") or request.data.get("id")
        if not transaction_id:
            logger.info("payment.webhook.stub: missing_transaction_id")
        else:
            payment = (
                Payment.objects.filter(transaction_id=transaction_id)
                .select_related("reservation", "reservation__listing", "user")
                .first()
            )
            if not payment:
                logger.info(
                    "payment.webhook.stub: transaction_id=%s not_found",
                    transaction_id,
                )
            elif not may_complete_stub_webhook(request=request, payment=payment):
                logger.warning(
                    "payment.webhook.stub: denied payment_id=%s transaction_id=%s",
                    payment.id,
                    transaction_id,
                )
            else:
                set_request_user_id_for_rls(payment.user_id)
                was_completed = payment.status == "completed"
                payment.status = "completed"
                payment.save()
                logger.info(
                    "payment.webhook.stub: payment_id=%s transaction_id=%s "
                    "was_completed=%s",
                    payment.id,
                    transaction_id,
                    was_completed,
                )
                if not was_completed:
                    from .hooks import on_payment_first_completed

                    on_payment_first_completed(payment)

        return Response(
            {"received": True, "provider": "stub"}, status=status.HTTP_200_OK
        )


@method_decorator(csrf_exempt, name="dispatch")
class PaymentWebhookStripeView(APIView):
    """
    POST: Stripe webhook - verifies Stripe-Signature, handles checkout.session.completed.
    Configure Stripe Dashboard to point to: {BACKEND_URL}/api/payments/webhook/stripe/
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        from .stripe_service import handle_stripe_webhook

        return handle_stripe_webhook(request)


# Backwards-compatible alias
PaymentWebhookView = PaymentWebhookStubView
