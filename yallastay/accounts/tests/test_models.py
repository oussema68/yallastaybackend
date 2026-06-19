from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import (
    UserProfile,
    LandlordProfile,
    RealtorProfile,
    UAEIDVerification,
    UniversityVerification,
)
from core.models import University

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            email="test@example.com", password="TestPass123!"
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("TestPass123!"))
        self.assertEqual(str(user), "test@example.com")

    def test_create_user_no_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="pass")


class UserProfileModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="Pass123!"
        )

    def test_create_profile(self):
        profile = UserProfile.objects.create(user=self.user, role="tenant")
        self.assertEqual(profile.role, "tenant")
        self.assertFalse(profile.is_email_verified)
        self.assertIsNone(profile.email_verified_at)
        self.assertEqual(str(profile), f"{self.user.email} (tenant)")


class LandlordProfileModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="landlord@example.com", password="Pass123!"
        )

    def test_create_landlord_profile(self):
        lp = LandlordProfile.objects.create(user=self.user, company_name="My Rentals")
        self.assertEqual(lp.company_name, "My Rentals")
        self.assertEqual(str(lp), f"Landlord: {self.user.email}")


class RealtorProfileModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="realtor@example.com", password="Pass123!"
        )

    def test_create_realtor_profile(self):
        rp = RealtorProfile.objects.create(
            user=self.user, agency_name="Dubai Property Co"
        )
        self.assertEqual(rp.agency_name, "Dubai Property Co")
        self.assertFalse(rp.is_approved)
        self.assertEqual(str(rp), f"Realtor: Dubai Property Co ({self.user.email})")


class UAEIDVerificationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )

    def test_create_verification(self):
        v = UAEIDVerification.objects.create(
            user=self.user, id_hash="abc123", status="approved"
        )
        self.assertEqual(v.status, "approved")
        self.assertEqual(v.user, self.user)


class UniversityVerificationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student@uaeu.ac.ae", password="Pass123!"
        )
        self.uni = University.objects.create(name="UAE University", domain="uaeu.ac.ae")

    def test_create_university_verification(self):
        v = UniversityVerification.objects.create(
            user=self.user, university=self.uni, student_id="12345", status="approved"
        )
        self.assertEqual(v.status, "approved")
        self.assertEqual(v.university, self.uni)
