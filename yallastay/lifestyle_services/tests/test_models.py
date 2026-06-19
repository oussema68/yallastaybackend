from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile, LandlordProfile
from core.models import Area
from listings.models import Listing
from bookings.models import Reservation
from lifestyle_services.models import (
    LifestylePlan,
    LifestyleService,
    LifestyleSubscription,
)

User = get_user_model()


def _landlord():
    user = User.objects.create_user(email="landlord@example.com", password="Pass123!")
    UserProfile.objects.create(user=user, role="landlord")
    LandlordProfile.objects.create(user=user)
    return user


class LifestylePlanModelTests(TestCase):
    def test_create_plan(self):
        plan = LifestylePlan.objects.create(name="Essential", tier=1, price=299)
        self.assertEqual(plan.name, "Essential")
        self.assertEqual(plan.price, 299)


class LifestyleServiceModelTests(TestCase):
    def setUp(self):
        self.plan = LifestylePlan.objects.create(name="Comfort", tier=2, price=499)

    def test_create_service(self):
        svc = LifestyleService.objects.create(
            plan=self.plan, service_type="cleaning", details="Weekly"
        )
        self.assertEqual(svc.service_type, "cleaning")
        self.assertEqual(svc.plan, self.plan)


class LifestyleSubscriptionModelTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        landlord = _landlord()
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
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

    def test_create_subscription(self):
        sub = LifestyleSubscription.objects.create(
            reservation=self.reservation,
            plan=self.plan,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="active",
        )
        self.assertEqual(sub.status, "active")
        self.assertEqual(sub.user, self.user)
