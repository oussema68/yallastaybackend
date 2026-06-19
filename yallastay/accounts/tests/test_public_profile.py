from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import (
    UserProfile,
    LandlordProfile,
    RealtorProfile,
    UAEIDVerification,
)
from core.models import Area
from listings.models import Listing
from messaging.models import Conversation
from reviews.models import Review

User = get_user_model()


class PublicProfileViewTests(APITestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Marina", slug="marina")
        self.tenant = User.objects.create_user(
            email="t@example.com", password="Pass123!", first_name="Tina"
        )
        UserProfile.objects.create(
            user=self.tenant, role="tenant", phone="+971500000001"
        )
        self.landlord = User.objects.create_user(
            email="l@example.com", password="Pass123!", first_name="Leo"
        )
        UserProfile.objects.create(user=self.landlord, role="landlord")
        LandlordProfile.objects.create(user=self.landlord)
        self.realtor = User.objects.create_user(
            email="r@example.com", password="Pass123!", first_name="Ray"
        )
        UserProfile.objects.create(user=self.realtor, role="realtor")
        RealtorProfile.objects.create(
            user=self.realtor,
            agency_name="Ray Realty",
            is_approved=True,
            rera_number="12345",
        )
        self.listing = Listing.objects.create(
            title="Apt",
            description="d",
            price=4000,
            type="apartment",
            area=self.area,
            listed_by=self.realtor,
        )

    def test_requires_auth(self):
        response = self.client.get(f"/api/auth/users/{self.tenant.id}/public-profile/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_minimal_profile_and_reviews(self):
        Review.objects.create(
            reviewer=self.tenant,
            reviewee=self.realtor,
            listing=self.listing,
            rating=5,
            comment="Great broker",
        )
        self.client.force_authenticate(user=self.landlord)
        with self.assertLogs("accounts.public_profile_views", level="INFO") as cm:
            response = self.client.get(
                f"/api/auth/users/{self.realtor.id}/public-profile/"
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any("accounts.public_profile.ok" in r.getMessage() for r in cm.records)
        )
        self.assertEqual(response.data["first_name"], "Ray")
        self.assertEqual(response.data["role"], "realtor")
        self.assertIn("realtor_public", response.data)
        self.assertEqual(response.data["realtor_public"]["agency_name"], "Ray Realty")
        self.assertEqual(response.data["review_summary"]["count"], 1)
        self.assertEqual(len(response.data["reviews"]), 1)
        self.assertEqual(
            response.data["reviews"][0]["reviewer_label"], "Verified renter"
        )
        self.assertNotIn("@example.com", str(response.data))

    def test_contract_context_when_shared_conversation(self):
        UAEIDVerification.objects.create(
            user=self.tenant, id_hash="x", status="approved"
        )
        conv = Conversation.objects.create(listing=self.listing)
        conv.participants.add(self.tenant, self.realtor)
        self.client.force_authenticate(user=self.realtor)
        response = self.client.get(f"/api/auth/users/{self.tenant.id}/public-profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["contract_context"])
        self.assertEqual(response.data["contract_context"]["phone"], "+971500000001")

    def test_no_contract_context_without_relationship(self):
        self.client.force_authenticate(user=self.landlord)
        response = self.client.get(f"/api/auth/users/{self.tenant.id}/public-profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["contract_context"])
