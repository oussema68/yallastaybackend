from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import UserProfile, RealtorProfile, LandlordProfile
from core.models import Area
from listings.models import Listing

User = get_user_model()


class AnalyticsViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        self.realtor = User.objects.create_user(
            email="realtor@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.realtor, role="realtor")
        rp = RealtorProfile.objects.create(user=self.realtor, agency_name="Test Agency")
        rp.is_approved = True
        rp.save()

    def test_analytics_requires_auth(self):
        response = self.client.get("/api/analytics/renter-demographics/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_popular_areas_requires_auth(self):
        response = self.client.get("/api/analytics/popular-areas/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_renter_demographics_as_realtor(self):
        self.client.force_authenticate(user=self.realtor)
        response = self.client.get("/api/analytics/renter-demographics/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_popular_areas_as_realtor(self):
        self.client.force_authenticate(user=self.realtor)
        response = self.client.get("/api/analytics/popular-areas/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_my_listings_insights_as_realtor(self):
        self.client.force_authenticate(user=self.realtor)
        response = self.client.get("/api/analytics/my-listings-insights/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_my_listings_insights_includes_assigned_listings_for_realtor(self):
        """Metrics include listings where the realtor is assigned by the owner (not only listed_by)."""
        area = Area.objects.create(name="JVC", slug="jvc")
        landlord = User.objects.create_user(
            email="owner-insights@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=landlord, role="landlord")
        LandlordProfile.objects.create(user=landlord)
        Listing.objects.create(
            title="Owner unit",
            description="x",
            price=3000,
            type="apartment",
            area=area,
            listed_by=landlord,
            assigned_realtor=self.realtor,
        )
        self.client.force_authenticate(user=self.realtor)
        response = self.client.get("/api/analytics/my-listings-insights/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_listings"], 1)

    def test_analytics_non_realtor_returns_403(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/analytics/renter-demographics/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_listings_insights_as_landlord(self):
        from accounts.models import LandlordProfile

        landlord = User.objects.create_user(
            email="landlord2@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=landlord, role="landlord")
        LandlordProfile.objects.create(user=landlord)
        self.client.force_authenticate(user=landlord)
        response = self.client.get("/api/analytics/my-listings-insights/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_listings"], 0)
