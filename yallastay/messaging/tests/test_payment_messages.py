"""Unit tests for payment → team message workflow (with logging assertions)."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import LandlordProfile, UserProfile
from bookings.models import Reservation
from core.models import Area
from listings.models import Listing
from messaging.models import Message
from messaging.payment_messages import notify_realtor_rental_payment_received
from payments.models import Payment

User = get_user_model()


class NotifyRealtorPaymentTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="DM", slug="dm")
        self.landlord = User.objects.create_user(
            email="l@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.landlord, role="landlord")
        LandlordProfile.objects.create(user=self.landlord)
        self.renter = User.objects.create_user(
            email="r@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.renter, role="tenant")
        self.listing = Listing.objects.create(
            title="Unit",
            description="d",
            price=4000,
            type="apartment",
            area=self.area,
            listed_by=self.landlord,
        )
        self.reservation = Reservation.objects.create(
            listing=self.listing,
            user=self.renter,
            start_date="2026-04-01",
            end_date="2027-03-31",
            status="pending",
        )

    def test_skip_logs_wrong_type(self):
        p = Payment.objects.create(
            user=self.renter,
            amount=100,
            payment_type="fee",
            status="completed",
            transaction_id="ys_fee",
            reservation=self.reservation,
        )
        with self.assertLogs("messaging.payment_messages", level="INFO") as cm:
            self.assertFalse(notify_realtor_rental_payment_received(p))
        self.assertTrue(
            any("payment.team_message.skip" in r.getMessage() for r in cm.records)
        )
        self.assertTrue(any("wrong_type" in r.getMessage() for r in cm.records))

    def test_sent_logs_and_creates_message(self):
        p = Payment.objects.create(
            user=self.renter,
            amount=5000,
            payment_type="rent",
            status="completed",
            transaction_id="ys_ok",
            reservation=self.reservation,
        )
        with self.assertLogs("messaging.payment_messages", level="INFO") as cm:
            self.assertTrue(notify_realtor_rental_payment_received(p))
        self.assertTrue(
            any("payment.team_message.sent" in r.getMessage() for r in cm.records)
        )
        self.assertTrue(
            Message.objects.filter(conversation__listing=self.listing).exists()
        )
        p.refresh_from_db()
        self.assertIsNotNone(p.team_message_sent_at)
