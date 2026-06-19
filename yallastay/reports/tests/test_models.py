from django.contrib.auth import get_user_model
from django.test import TestCase

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


class ReportModelTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.reporter = User.objects.create_user(
            email="reporter@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.reporter, role="tenant")
        landlord = _landlord()
        self.listing = Listing.objects.create(
            title="Test",
            description="",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )

    def test_create_report_listing(self):
        r = Report.objects.create(
            reporter=self.reporter, reported_listing=self.listing, reason="spam"
        )
        self.assertEqual(r.status, "pending")
        self.assertEqual(
            str(r), f"Report by {self.reporter.email} → {self.listing.title} (pending)"
        )
