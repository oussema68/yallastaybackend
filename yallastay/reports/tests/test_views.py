from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import UserProfile, LandlordProfile
from core.models import Area
from listings.models import Listing
from reports.models import Report

User = get_user_model()


def _landlord():
    user = User.objects.create_user(email="landlord@example.com", password="Pass123!")
    UserProfile.objects.create(user=user, role="landlord")
    LandlordProfile.objects.create(user=user)
    return user


class ReportViewTests(APITestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        landlord = _landlord()
        self.listing = Listing.objects.create(
            title="Test",
            description="Desc",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )
        self.reported_user = User.objects.create_user(
            email="reported@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.reported_user, role="tenant")

    def test_list_reports_requires_auth(self):
        response = self.client.get("/api/reports/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_submit_report_requires_auth(self):
        response = self.client.post(
            "/api/reports/submit/",
            {
                "listing_id": self.listing.id,
                "reason": "spam",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_submit_report_listing_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/reports/submit/",
            {
                "listing_id": self.listing.id,
                "reason": "Spam listing",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Report.objects.filter(
                reporter=self.user, reported_listing=self.listing
            ).exists()
        )

    def test_submit_report_user_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/reports/submit/",
            {
                "user_id": self.reported_user.id,
                "reason": "Harassment",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Report.objects.filter(
                reporter=self.user, reported_user=self.reported_user
            ).exists()
        )

    def test_submit_report_both_listing_and_user_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/reports/submit/",
            {
                "listing_id": self.listing.id,
                "user_id": self.reported_user.id,
                "reason": "Something",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_report_neither_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/reports/submit/",
            {
                "reason": "No target",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_own_reports(self):
        Report.objects.create(
            reporter=self.user, reported_listing=self.listing, reason="spam"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/reports/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_report_detail_as_reporter(self):
        r = Report.objects.create(
            reporter=self.user, reported_listing=self.listing, reason="spam"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/reports/{r.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_report_detail_non_reporter_returns_404(self):
        other = User.objects.create_user(
            email="other2@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=other, role="tenant")
        r = Report.objects.create(
            reporter=other, reported_listing=self.listing, reason="spam"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/reports/{r.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_can_patch_report(self):
        self.user.is_staff = True
        self.user.save()
        r = Report.objects.create(
            reporter=self.user, reported_listing=self.listing, reason="spam"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/reports/{r.id}/",
            {
                "status": "resolved",
                "admin_notes": "Handled",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        r.refresh_from_db()
        self.assertEqual(r.status, "resolved")
