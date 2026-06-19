"""Lifestyle management dashboard API (staff, superuser, or profile flag)."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import UserProfile, LandlordProfile
from core.models import Area
from listings.models import Listing
from bookings.models import Reservation
from lifestyle_services.models import LifestylePlan, LifestyleSubscription
from payments.models import Payment

User = get_user_model()


def _landlord():
    user = User.objects.create_user(email="landlord@example.com", password="Pass123!")
    UserProfile.objects.create(user=user, role="landlord")
    LandlordProfile.objects.create(user=user)
    return user


class LifestyleManagementOverviewTests(APITestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        landlord = _landlord()
        self.tenant = User.objects.create_user(
            email="tenant@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.tenant, role="tenant")
        self.listing = Listing.objects.create(
            title="Test Unit",
            description="",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )
        self.plan = LifestylePlan.objects.create(name="Essential", tier=1, price=300)
        self.reservation = Reservation.objects.create(
            listing=self.listing,
            user=self.tenant,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="confirmed",
        )
        self.sub = LifestyleSubscription.objects.create(
            reservation=self.reservation,
            plan=self.plan,
            user=self.tenant,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="active",
        )
        Payment.objects.create(
            user=self.tenant,
            amount=self.plan.price,
            currency="AED",
            payment_type="lifestyle",
            status="completed",
            reservation=self.reservation,
            lifestyle_subscription=self.sub,
            transaction_id="tx_1",
        )

        self.staff = User.objects.create_user(
            email="staff@example.com", password="Pass123!", is_staff=True
        )
        UserProfile.objects.create(user=self.staff, role="tenant")

        self.regular = User.objects.create_user(
            email="regular@example.com", password="Pass123!", is_staff=False
        )
        UserProfile.objects.create(user=self.regular, role="tenant")

    def test_overview_requires_auth(self):
        response = self.client.get("/api/lifestyle-management/overview/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_overview_forbidden_non_staff(self):
        self.client.force_authenticate(user=self.regular)
        response = self.client.get("/api/lifestyle-management/overview/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_overview_allowed_for_can_manage_lifestyle_without_staff(self):
        mgr = User.objects.create_user(
            email="lifestyle_mgr@example.com", password="Pass123!", is_staff=False
        )
        UserProfile.objects.create(user=mgr, role="tenant", can_manage_lifestyle=True)
        self.client.force_authenticate(user=mgr)
        response = self.client.get("/api/lifestyle-management/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_overview_staff_returns_summary_and_results(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/api/lifestyle-management/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("summary", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["summary"]["total_subscriptions"], 1)
        self.assertEqual(response.data["summary"]["by_status"].get("active"), 1)
        self.assertEqual(len(response.data["results"]), 1)
        row = response.data["results"][0]
        self.assertEqual(row["user_email"], "tenant@example.com")
        self.assertEqual(row["plan_name"], "Essential")
        self.assertEqual(row["listing_title"], "Test Unit")
        self.assertEqual(row["status"], "active")
        self.assertIsNotNone(row["latest_payment"])
        self.assertEqual(row["latest_payment"]["status"], "completed")

    def test_overview_status_filter(self):
        LifestyleSubscription.objects.create(
            reservation=self.reservation,
            plan=self.plan,
            user=self.tenant,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="cancelled",
        )
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(
            "/api/lifestyle-management/overview/", {"status": "cancelled"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["status"], "cancelled")
