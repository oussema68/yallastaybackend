from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile
from core.models import Area
from roommates.models import RoommateProfile, RoommateInterest

User = get_user_model()


class RoommateProfileModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")

    def test_create_roommate_profile(self):
        profile = RoommateProfile.objects.create(
            user=self.user, bio="Looking for roommate", budget_min=2000, budget_max=4000
        )
        profile.preferred_areas.add(self.area)
        self.assertEqual(profile.bio, "Looking for roommate")
        self.assertTrue(profile.is_looking)
        self.assertEqual(str(profile), f"Roommate: {self.user.email}")


class RoommateInterestModelTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            email="user1@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user1, role="tenant")
        self.user2 = User.objects.create_user(
            email="user2@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user2, role="tenant")

    def test_create_interest(self):
        interest = RoommateInterest.objects.create(
            from_user=self.user1, to_user=self.user2, message="Hi!"
        )
        self.assertEqual(interest.status, "pending")
        self.assertEqual(
            str(interest), f"{self.user1.email} → {self.user2.email} (pending)"
        )
