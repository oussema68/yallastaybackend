"""Lifestyle plan sections/benefits (CMS-style content)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import UserProfile
from lifestyle_services.models import (
    LifestylePlan,
    LifestylePlanBenefit,
    LifestylePlanSection,
    LifestyleService,
)

User = get_user_model()


class LifestylePlanSectionModelTests(TestCase):
    def test_section_and_benefits_ordering(self):
        plan = LifestylePlan.objects.create(name="Essential", tier=1, price=300)
        sec = LifestylePlanSection.objects.create(
            plan=plan, title="Wellness", emoji="🏋️", sort_order=0
        )
        LifestylePlanBenefit.objects.create(
            section=sec, text="Gym access", sort_order=1
        )
        LifestylePlanBenefit.objects.create(
            section=sec, text="Pool access", sort_order=0
        )
        benefits = list(sec.benefits.values_list("text", flat=True))
        self.assertEqual(benefits, ["Pool access", "Gym access"])


class LifestylePlanListApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        self.plan = LifestylePlan.objects.create(
            name="Essential",
            tier=1,
            price=300,
            tagline="Young professionals",
            is_most_popular=False,
            is_active=True,
        )
        sec = LifestylePlanSection.objects.create(
            plan=self.plan, title="Home", emoji="🏠", sort_order=0
        )
        LifestylePlanBenefit.objects.create(
            section=sec, text="2× cleaning/month", sort_order=0
        )
        LifestyleService.objects.create(
            plan=self.plan, service_type="gym", details="Partner"
        )

    def test_plan_includes_sections_tagline_and_services(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/lifestyle-plans/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        row = response.data[0]
        self.assertEqual(row["name"], "Essential")
        self.assertEqual(row["tagline"], "Young professionals")
        self.assertFalse(row["is_most_popular"])
        self.assertEqual(len(row["sections"]), 1)
        self.assertEqual(row["sections"][0]["title"], "Home")
        self.assertEqual(row["sections"][0]["emoji"], "🏠")
        self.assertEqual(len(row["sections"][0]["benefits"]), 1)
        self.assertEqual(row["sections"][0]["benefits"][0]["text"], "2× cleaning/month")
        self.assertEqual(len(row["services"]), 1)

    def test_inactive_plan_excluded_from_list(self):
        LifestylePlan.objects.create(
            name="Retired",
            tier=99,
            price=999,
            is_active=False,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/lifestyle-plans/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data]
        self.assertIn("Essential", names)
        self.assertNotIn("Retired", names)


class LifestyleSubscribeInactivePlanTests(APITestCase):
    """Subscription POST only accepts active plans."""

    def setUp(self):
        from core.models import Area
        from listings.models import Listing
        from accounts.models import LandlordProfile
        from bookings.models import Reservation

        def _landlord():
            u = User.objects.create_user(
                email="landlord@example.com", password="Pass123!"
            )
            UserProfile.objects.create(user=u, role="landlord")
            LandlordProfile.objects.create(user=u)
            return u

        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        landlord = _landlord()
        self.listing = Listing.objects.create(
            title="Test",
            description="Desc",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )
        self.plan = LifestylePlan.objects.create(
            name="Inactive", tier=5, price=100, is_active=False
        )
        self.reservation = Reservation.objects.create(
            listing=self.listing,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="confirmed",
        )

    def test_create_subscription_rejects_inactive_plan(self):
        from accounts.models import UAEIDVerification

        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/lifestyle-subscriptions/",
            {
                "plan_id": self.plan.id,
                "reservation_id": self.reservation.id,
                "start_date": "2026-04-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
