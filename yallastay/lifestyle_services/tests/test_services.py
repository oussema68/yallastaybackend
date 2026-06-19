"""Unit tests for lifestyle_services.services (payment activation + cancel helpers)."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile, LandlordProfile
from core.models import Area
from listings.models import Listing
from bookings.models import Reservation
from lifestyle_services.models import LifestylePlan, LifestyleSubscription
from lifestyle_services.services import (
    activate_subscription_after_payment,
    cancel_pending_subscription_payment,
)
from payments.models import Payment

User = get_user_model()


def _landlord():
    u = User.objects.create_user(email="landlord@example.com", password="Pass123!")
    UserProfile.objects.create(user=u, role="landlord")
    LandlordProfile.objects.create(user=u)
    return u


class LifestyleServicesModuleTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        landlord = _landlord()
        self.user = User.objects.create_user(
            email="renter@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        self.listing = Listing.objects.create(
            title="Test",
            description="",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )
        self.plan = LifestylePlan.objects.create(name="Essential", tier=1, price=299)
        self.reservation = Reservation.objects.create(
            listing=self.listing,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="confirmed",
        )

    def test_activate_subscription_after_payment_sets_active(self):
        sub = LifestyleSubscription.objects.create(
            reservation=self.reservation,
            plan=self.plan,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="pending_payment",
        )
        payment = Payment.objects.create(
            user=self.user,
            amount=self.plan.price,
            currency="AED",
            payment_type="lifestyle",
            status="completed",
            reservation=self.reservation,
            lifestyle_subscription=sub,
            transaction_id="ys_test",
        )
        activate_subscription_after_payment(payment)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "active")

    def test_activate_subscription_idempotent_when_already_active(self):
        sub = LifestyleSubscription.objects.create(
            reservation=self.reservation,
            plan=self.plan,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="active",
        )
        payment = Payment.objects.create(
            user=self.user,
            amount=self.plan.price,
            currency="AED",
            payment_type="lifestyle",
            status="completed",
            reservation=self.reservation,
            lifestyle_subscription=sub,
            transaction_id="ys_test",
        )
        activate_subscription_after_payment(payment)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "active")

    def test_activate_skips_non_lifestyle_payment(self):
        sub = LifestyleSubscription.objects.create(
            reservation=self.reservation,
            plan=self.plan,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="pending_payment",
        )
        payment = Payment.objects.create(
            user=self.user,
            amount=100,
            currency="AED",
            payment_type="fee",
            status="completed",
            lifestyle_subscription=sub,
            transaction_id="ys_fee",
        )
        activate_subscription_after_payment(payment)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "pending_payment")

    def test_cancel_pending_subscription_payment_marks_payment_cancelled(self):
        sub = LifestyleSubscription.objects.create(
            reservation=self.reservation,
            plan=self.plan,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="pending_payment",
        )
        pay = Payment.objects.create(
            user=self.user,
            amount=self.plan.price,
            currency="AED",
            payment_type="lifestyle",
            status="pending",
            reservation=self.reservation,
            lifestyle_subscription=sub,
            transaction_id="ys_pend",
        )
        cancel_pending_subscription_payment(sub)
        pay.refresh_from_db()
        self.assertEqual(pay.status, "cancelled")

    def test_cancel_pending_subscription_payment_noop_when_not_pending_payment(self):
        sub = LifestyleSubscription.objects.create(
            reservation=self.reservation,
            plan=self.plan,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="active",
        )
        pay = Payment.objects.create(
            user=self.user,
            amount=self.plan.price,
            currency="AED",
            payment_type="lifestyle",
            status="completed",
            reservation=self.reservation,
            lifestyle_subscription=sub,
            transaction_id="ys_done",
        )
        cancel_pending_subscription_payment(sub)
        pay.refresh_from_db()
        self.assertEqual(pay.status, "completed")
