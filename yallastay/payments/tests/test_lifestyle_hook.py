"""on_payment_first_completed activates lifestyle subscriptions (integration)."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile, LandlordProfile
from core.models import Area
from listings.models import Listing
from bookings.models import Reservation
from lifestyle_services.models import LifestylePlan, LifestyleSubscription
from payments.hooks import on_payment_first_completed
from payments.models import Payment

User = get_user_model()


def _landlord():
    u = User.objects.create_user(email="landlord2@example.com", password="Pass123!")
    UserProfile.objects.create(user=u, role="landlord")
    LandlordProfile.objects.create(user=u)
    return u


class LifestylePaymentHookTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="DM", slug="dm")
        landlord = _landlord()
        self.user = User.objects.create_user(
            email="hook@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        self.listing = Listing.objects.create(
            title="L",
            description="",
            price=4000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )
        self.plan = LifestylePlan.objects.create(name="Comfort", tier=2, price=400)
        self.reservation = Reservation.objects.create(
            listing=self.listing,
            user=self.user,
            start_date="2026-05-01",
            end_date="2027-11-01",
            status="confirmed",
        )

    def test_on_payment_first_completed_activates_lifestyle_subscription(self):
        sub = LifestyleSubscription.objects.create(
            reservation=self.reservation,
            plan=self.plan,
            user=self.user,
            start_date="2026-05-01",
            end_date="2027-11-01",
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
            transaction_id="ys_hook",
        )
        on_payment_first_completed(payment)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "active")
