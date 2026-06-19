from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import RealtorProfile, UserProfile

User = get_user_model()


class VerifiedRealtorsApiTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.owner, role="landlord")

        u1 = User.objects.create_user(email="priv@example.com", password="Pass123!")
        UserProfile.objects.create(user=u1, role="realtor")
        self.private = RealtorProfile.objects.create(
            user=u1, agency_name="Solo Broker", brokerage_type="private"
        )
        self.private.is_approved = True
        self.private.save()

        u2 = User.objects.create_user(email="ag@example.com", password="Pass123!")
        UserProfile.objects.create(user=u2, role="realtor")
        self.agency = RealtorProfile.objects.create(
            user=u2, agency_name="Agency Co", brokerage_type="agency"
        )
        self.agency.is_approved = True
        self.agency.save()

    def test_requires_auth(self):
        r = self.client.get("/api/auth/verified-realtors/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_private_before_agency(self):
        self.client.force_authenticate(user=self.owner)
        r = self.client.get("/api/auth/verified-realtors/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 2)
        self.assertEqual(r.data[0]["brokerage_type"], "private")
        self.assertEqual(r.data[1]["brokerage_type"], "agency")
