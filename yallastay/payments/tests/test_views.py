from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import LandlordProfile, UserProfile
from bookings.models import Reservation
from core.models import Area
from listings.models import Listing
from messaging.models import Message
from payments.models import Payment

User = get_user_model()


class PaymentViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )

    def test_list_payments_requires_auth(self):
        response = self.client.get("/api/payments/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_payments_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/payments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_initiate_payment(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/payments/initiate/",
            {
                "amount": 5000,
                "payment_type": "fee",
                "currency": "AED",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("payment_id", response.data)
        self.assertIn("checkout_url", response.data)
        self.assertTrue(
            Payment.objects.filter(user=self.user, status="pending").exists()
        )

    def test_initiate_rent_rejects_other_users_reservation(self):
        area = Area.objects.create(name="JLT", slug="jlt-pay")
        landlord = User.objects.create_user(email="ld@example.com", password="Pass123!")
        UserProfile.objects.create(user=landlord, role="landlord")
        LandlordProfile.objects.create(user=landlord)
        listing = Listing.objects.create(
            title="Other listing",
            description="",
            price=4000,
            type="apartment",
            area=area,
            listed_by=landlord,
        )
        victim = User.objects.create_user(
            email="victim@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=victim, role="tenant")
        start = timezone.now().date() + timedelta(days=5)
        end = start + timedelta(days=30)
        res = Reservation.objects.create(
            listing=listing,
            user=victim,
            start_date=start,
            end_date=end,
            status="confirmed",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/payments/initiate/",
            {
                "amount": "4000.00",
                "payment_type": "rent",
                "currency": "AED",
                "reservation_id": res.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reservation_id", response.data)

    def test_initiate_rent_rejects_lister_even_on_own_listing(self):
        area = Area.objects.create(name="Marina", slug="marina-pay2")
        landlord = User.objects.create_user(
            email="ld2@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=landlord, role="landlord")
        LandlordProfile.objects.create(user=landlord)
        listing = Listing.objects.create(
            title="Lister listing",
            description="",
            price=4000,
            type="apartment",
            area=area,
            listed_by=landlord,
        )
        tenant = User.objects.create_user(email="ten2@example.com", password="Pass123!")
        UserProfile.objects.create(user=tenant, role="tenant")
        start = timezone.now().date() + timedelta(days=5)
        end = start + timedelta(days=30)
        res = Reservation.objects.create(
            listing=listing,
            user=tenant,
            start_date=start,
            end_date=end,
            status="confirmed",
        )
        self.client.force_authenticate(user=landlord)
        response = self.client.post(
            "/api/payments/initiate/",
            {
                "amount": "4000.00",
                "payment_type": "rent",
                "currency": "AED",
                "reservation_id": res.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reservation_id", response.data)

    def test_webhook_marks_payment_completed(self):
        pmt = Payment.objects.create(
            user=self.user,
            amount=5000,
            payment_type="rent",
            status="pending",
            transaction_id="ys_abc123def456",
        )
        response = self.client.post(
            "/api/payments/webhook/",
            {
                "transaction_id": "ys_abc123def456",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pmt.refresh_from_db()
        self.assertEqual(pmt.status, "completed")

    @patch("payments.hooks.on_payment_first_completed")
    def test_webhook_calls_side_effect_once_when_retried(self, mock_hook):
        Payment.objects.create(
            user=self.user,
            amount=5000,
            payment_type="rent",
            status="pending",
            transaction_id="ys_idempotent_retry",
        )
        for _ in range(2):
            response = self.client.post(
                "/api/payments/webhook/stub/",
                {"transaction_id": "ys_idempotent_retry"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_hook.call_count, 1)

    def test_webhook_posts_yallastay_team_message_for_rent_reservation(self):
        area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        landlord = User.objects.create_user(
            email="landlord@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=landlord, role="landlord")
        LandlordProfile.objects.create(user=landlord)
        listing = Listing.objects.create(
            title="Marina 2BR",
            description="desc",
            price=5000,
            type="apartment",
            area=area,
            listed_by=landlord,
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        reservation = Reservation.objects.create(
            listing=listing,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-03-31",
            status="pending",
        )
        pmt = Payment.objects.create(
            user=self.user,
            amount=5000,
            payment_type="rent",
            status="pending",
            transaction_id="ys_rent_full",
            reservation=reservation,
        )
        with self.assertLogs("payments.views", level="INFO"):
            with self.assertLogs("messaging.payment_messages", level="INFO"):
                response = self.client.post(
                    "/api/payments/webhook/",
                    {"transaction_id": "ys_rent_full"},
                    format="json",
                )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        msg = Message.objects.filter(conversation__listing=listing).first()
        self.assertIsNotNone(msg)
        self.assertIn("yallastay team", msg.content.lower())
        self.assertIn("finalize", msg.content.lower())
        pmt.refresh_from_db()
        self.assertIsNotNone(pmt.team_message_sent_at)
        self.client.post(
            "/api/payments/webhook/",
            {"transaction_id": "ys_rent_full"},
            format="json",
        )
        self.assertEqual(
            Message.objects.filter(conversation__listing=listing).count(), 1
        )


class PaymentWorkflowLoggingTests(APITestCase):
    """Assert INFO logs at each step (stub initiate → webhook → team message)."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="loguser@example.com", password="Pass123!"
        )

    def test_initiate_stub_logs(self):
        self.client.force_authenticate(user=self.user)
        with self.assertLogs("payments.checkout", level="INFO") as cm:
            response = self.client.post(
                "/api/payments/initiate/",
                {
                    "amount": 100,
                    "payment_type": "fee",
                    "currency": "AED",
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            any("payment.checkout.stub" in r.getMessage() for r in cm.records)
        )

    def test_webhook_stub_logs_each_step(self):
        Payment.objects.create(
            user=self.user,
            amount=5000,
            payment_type="rent",
            status="pending",
            transaction_id="ys_log_step",
        )
        with self.assertLogs("payments.views", level="INFO") as cm:
            response = self.client.post(
                "/api/payments/webhook/stub/",
                {"transaction_id": "ys_log_step"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any("payment.webhook.stub" in r.getMessage() for r in cm.records)
        )

    def test_list_payments_logs_count(self):
        self.client.force_authenticate(user=self.user)
        Payment.objects.create(
            user=self.user,
            amount=10,
            payment_type="fee",
            status="completed",
            transaction_id="ys_l1",
        )
        with self.assertLogs("payments.views", level="INFO") as cm:
            response = self.client.get("/api/payments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any("payment.list" in r.getMessage() for r in cm.records))
