"""Stripe path (PAYMENT_PROVIDER=stripe). Requires ``stripe`` package (see requirements.txt)."""

import secrets
from unittest.mock import MagicMock, patch

import stripe
from django.test import SimpleTestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from payments.models import Payment
from payments.stripe_service import resolve_checkout_payment_method_label

User = get_user_model()

# Ephemeral non-committed values for mocked Stripe calls only (generated at import).
_MOCK_STRIPE_API_KEY = secrets.token_hex(32)
_MOCK_STRIPE_WEBHOOK_SECRET = secrets.token_hex(32)


@override_settings(
    PAYMENT_PROVIDER="stripe",
    STRIPE_SECRET_KEY=_MOCK_STRIPE_API_KEY,
    STRIPE_WEBHOOK_SECRET=_MOCK_STRIPE_WEBHOOK_SECRET,
    FRONTEND_URL="http://localhost:5173",
)
class StripePaymentTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="pay@example.com", password="Pass123!"
        )

    @patch("stripe.checkout.Session.create")
    def test_initiate_creates_checkout_session(self, mock_create):
        mock_create.return_value = MagicMock(
            id="cs_test_123",
            url="https://checkout.stripe.com/c/pay/cs_test_123",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/payments/initiate/",
            {
                "amount": "99.00",
                "payment_type": "fee",
                "currency": "AED",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["provider"], "stripe")
        self.assertIn("checkout.stripe.com", response.data["checkout_url"])
        self.assertEqual(response.data["stripe_session_id"], "cs_test_123")
        pmt = Payment.objects.get(user=self.user)
        self.assertEqual(pmt.transaction_id, "cs_test_123")

    @patch("stripe.checkout.Session.create")
    def test_initiate_logs_stripe_checkout_created(self, mock_create):
        mock_create.return_value = MagicMock(
            id="cs_log_1",
            url="https://checkout.stripe.com/pay/cs_log_1",
        )
        self.client.force_authenticate(user=self.user)
        with self.assertLogs("payments.stripe_service", level="INFO") as cm:
            self.client.post(
                "/api/payments/initiate/",
                {
                    "amount": "50.00",
                    "payment_type": "fee",
                    "currency": "AED",
                },
                format="json",
            )
        self.assertTrue(
            any("stripe.checkout.created" in r.getMessage() for r in cm.records)
        )

    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_completes_payment(self, mock_construct, mock_pi_retrieve):
        self.client.force_authenticate(user=self.user)
        pmt = Payment.objects.create(
            user=self.user,
            amount=100,
            payment_type="fee",
            status="pending",
            transaction_id="cs_resolve_1",
        )
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_resolve_1",
                    "payment_status": "paid",
                    "payment_intent": "pi_test_1",
                    "metadata": {"payment_id": str(pmt.id)},
                }
            },
        }
        mock_pi_retrieve.return_value = {
            "payment_method": {
                "type": "card",
                "card": {
                    "brand": "visa",
                    "wallet": {"type": "google_pay"},
                },
            }
        }
        with self.assertLogs("payments.stripe_service", level="INFO") as cm:
            response = self.client.post(
                "/api/payments/webhook/stripe/",
                b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="test_sig",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pmt.refresh_from_db()
        self.assertEqual(pmt.status, "completed")
        self.assertEqual(pmt.payment_method, "google_pay")
        self.assertTrue(
            any("stripe.webhook.completed" in r.getMessage() for r in cm.records)
        )

    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_stores_card_brand_without_wallet(
        self, mock_construct, mock_pi_retrieve
    ):
        pmt = Payment.objects.create(
            user=self.user,
            amount=50,
            payment_type="fee",
            status="pending",
            transaction_id="cs_card_only",
        )
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_card_only",
                    "payment_status": "paid",
                    "payment_intent": "pi_card_1",
                    "metadata": {"payment_id": str(pmt.id)},
                }
            },
        }
        mock_pi_retrieve.return_value = {
            "payment_method": {
                "type": "card",
                "card": {"brand": "mastercard"},
            }
        }
        response = self.client.post(
            "/api/payments/webhook/stripe/",
            b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pmt.refresh_from_db()
        self.assertEqual(pmt.payment_method, "card_mastercard")

    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_requires_signature_header(self, mock_construct):
        response = self.client.post(
            "/api/payments/webhook/stripe/",
            b"{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Stripe-Signature", response.data["detail"])
        mock_construct.assert_not_called()

    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_rejects_invalid_payload(self, mock_construct):
        mock_construct.side_effect = ValueError("bad json")
        response = self.client.post(
            "/api/payments/webhook/stripe/",
            b"not-json",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Invalid payload.")

    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_rejects_invalid_signature(self, mock_construct):
        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "bad", "sig-header"
        )
        response = self.client.post(
            "/api/payments/webhook/stripe/",
            b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="bad_sig",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Invalid signature.")

    @override_settings(STRIPE_WEBHOOK_SECRET="")
    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_missing_webhook_secret_returns_503(self, mock_construct):
        response = self.client.post(
            "/api/payments/webhook/stripe/",
            b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        mock_construct.assert_not_called()

    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_ignores_non_checkout_completed_event(
        self, mock_construct, mock_pi
    ):
        mock_construct.return_value = {
            "type": "charge.succeeded",
            "data": {"object": {"id": "ch_1"}},
        }
        response = self.client.post(
            "/api/payments/webhook/stripe/",
            b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("type"), "charge.succeeded")
        mock_pi.assert_not_called()

    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_ignores_session_not_paid(self, mock_construct, mock_pi):
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_unpaid",
                    "payment_status": "unpaid",
                    "payment_intent": None,
                }
            },
        }
        response = self.client.post(
            "/api/payments/webhook/stripe/",
            b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("ignored"), "not paid")
        mock_pi.assert_not_called()

    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_no_matching_payment_returns_200(
        self, mock_construct, mock_pi
    ):
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_unknown",
                    "payment_status": "paid",
                    "payment_intent": "pi_x",
                    "metadata": {},
                }
            },
        }
        mock_pi.return_value = {"payment_method": {"type": "card", "card": {}}}
        response = self.client.post(
            "/api/payments/webhook/stripe/",
            b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("note"), "no matching payment")

    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_resolves_payment_by_session_id_only(
        self, mock_construct, mock_pi
    ):
        pmt = Payment.objects.create(
            user=self.user,
            amount=10,
            payment_type="fee",
            status="pending",
            transaction_id="cs_id_only",
        )
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_id_only",
                    "payment_status": "paid",
                    "payment_intent": "pi_1",
                    "metadata": {},
                }
            },
        }
        mock_pi.return_value = {
            "payment_method": {"type": "card", "card": {"brand": "visa"}}
        }
        response = self.client.post(
            "/api/payments/webhook/stripe/",
            b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pmt.refresh_from_db()
        self.assertEqual(pmt.status, "completed")
        self.assertEqual(pmt.payment_method, "card_visa")

    @patch("payments.hooks.on_payment_first_completed")
    @patch("stripe.PaymentIntent.retrieve")
    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_calls_on_payment_first_completed_only_once(
        self, mock_construct, mock_pi, mock_hook
    ):
        pmt = Payment.objects.create(
            user=self.user,
            amount=20,
            payment_type="fee",
            status="pending",
            transaction_id="cs_idem_1",
        )
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_idem_1",
                    "payment_status": "paid",
                    "payment_intent": "pi_idem",
                    "metadata": {"payment_id": str(pmt.id)},
                }
            },
        }
        mock_construct.return_value = event
        mock_pi.return_value = {"payment_method": {"type": "card", "card": {}}}
        for _ in range(2):
            r = self.client.post(
                "/api/payments/webhook/stripe/",
                b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig",
            )
            self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_hook.call_count, 1)


class ResolveCheckoutPaymentMethodLabelTests(SimpleTestCase):
    @patch("stripe.PaymentIntent.retrieve")
    def test_empty_when_no_payment_intent(self, mock_pi):
        self.assertEqual(resolve_checkout_payment_method_label({}), "")
        self.assertEqual(
            resolve_checkout_payment_method_label({"id": "cs_1"}),
            "",
        )
        mock_pi.assert_not_called()

    @patch("stripe.PaymentIntent.retrieve")
    def test_apple_pay_wallet(self, mock_pi):
        mock_pi.return_value = {
            "payment_method": {
                "type": "card",
                "card": {"wallet": {"type": "apple_pay"}},
            }
        }
        self.assertEqual(
            resolve_checkout_payment_method_label({"payment_intent": "pi_1"}),
            "apple_pay",
        )

    @patch("stripe.PaymentIntent.retrieve")
    def test_samsung_pay_wallet(self, mock_pi):
        mock_pi.return_value = {
            "payment_method": {
                "type": "card",
                "card": {"wallet": {"type": "samsung_pay"}},
            }
        }
        self.assertEqual(
            resolve_checkout_payment_method_label({"payment_intent": "pi_1"}),
            "samsung_pay",
        )

    @patch("stripe.PaymentIntent.retrieve")
    def test_returns_empty_when_pi_retrieve_fails(self, mock_pi):
        mock_pi.side_effect = stripe.error.StripeError("network")
        self.assertEqual(
            resolve_checkout_payment_method_label({"payment_intent": "pi_bad"}),
            "",
        )

    @patch("stripe.PaymentMethod.retrieve")
    @patch("stripe.PaymentIntent.retrieve")
    def test_resolves_when_payment_method_is_id_string(self, mock_pi, mock_pm):
        mock_pi.return_value = {"payment_method": "pm_abc"}
        mock_pm.return_value = {
            "type": "card",
            "card": {"brand": "amex"},
        }
        self.assertEqual(
            resolve_checkout_payment_method_label({"payment_intent": "pi_1"}),
            "card_amex",
        )

    @patch("stripe.PaymentIntent.retrieve")
    def test_non_card_type_returns_type(self, mock_pi):
        mock_pi.return_value = {
            "payment_method": {
                "type": "link",
            }
        }
        self.assertEqual(
            resolve_checkout_payment_method_label({"payment_intent": "pi_1"}),
            "link",
        )
