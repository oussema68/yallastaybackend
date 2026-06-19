from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import UserProfile, UAEIDVerification
from core.models import Area

User = get_user_model()


class RoommateViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")

    def test_profile_requires_auth(self):
        response = self.client.get("/api/roommates/profile/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_requires_auth(self):
        response = self.client.get("/api/roommates/search/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_none_returns_200_null(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/roommates/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data)

    def test_create_profile_requires_uae_id(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/roommates/profile/",
            {
                "bio": "Looking for roommate",
                "budget_min": 2000,
                "budget_max": 4000,
                "preferred_area_ids": [self.area.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_profile_with_uae_id(self):
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/roommates/profile/",
            {
                "bio": "Student looking for roommate",
                "budget_min": 2000,
                "budget_max": 4000,
                "preferred_area_ids": [self.area.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.user.roommate_profile)

    def test_create_profile_rejects_budget_min_greater_than_max(self):
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/roommates/profile/",
            {
                "bio": "Hi",
                "budget_min": 5000,
                "budget_max": 2000,
                "preferred_area_ids": [self.area.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("budget_max", response.data)

    def test_create_profile_accepts_null_lifestyle_preferences(self):
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/roommates/profile/",
            {
                "bio": "Hi",
                "budget_min": 2000,
                "budget_max": 4000,
                "preferred_area_ids": [self.area.id],
                "lifestyle_preferences": None,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.user.roommate_profile.lifestyle_preferences, "")

    def test_landlord_cannot_use_roommate_features(self):
        landlord = User.objects.create_user(
            email="landlord@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=landlord, role="landlord")
        self.client.force_authenticate(user=landlord)
        response = self.client.get("/api/roommates/profile/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_profile(self):
        from roommates.models import RoommateProfile

        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        RoommateProfile.objects.create(
            user=self.user, bio="Initial", budget_min=2000, budget_max=4000
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            "/api/roommates/profile/", {"bio": "Updated bio"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.roommate_profile.refresh_from_db()
        self.assertEqual(self.user.roommate_profile.bio, "Updated bio")

    def test_search_roommates(self):
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/roommates/search/?area={self.area.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_includes_renter_profile_fields_and_age_filter(self):
        other = User.objects.create_user(email="other@example.com", password="Pass123!")
        UserProfile.objects.create(
            user=other,
            role="tenant",
            age=25,
            sex="male",
            place_of_work_or_studies="Dubai Tech Co.",
        )
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        UAEIDVerification.objects.create(user=other, id_hash="def", status="approved")
        from roommates.models import RoommateProfile

        RoommateProfile.objects.create(
            user=other, bio="Hey", is_looking=True, budget_min=1000, budget_max=5000
        )
        other.roommate_profile.preferred_areas.add(self.area)
        self.client.force_authenticate(user=self.user)
        r = self.client.get("/api/roommates/search/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        row = r.data[0]
        self.assertEqual(row["age"], 25)
        self.assertEqual(row["sex"], "male")
        self.assertEqual(row["place_of_work_or_studies"], "Dubai Tech Co.")
        r2 = self.client.get("/api/roommates/search/?age_min=30")
        self.assertEqual(len(r2.data), 0)
        r3 = self.client.get("/api/roommates/search/?age_max=25&sex=male")
        self.assertEqual(len(r3.data), 1)

    def test_express_interest(self):
        other = User.objects.create_user(email="other@example.com", password="Pass123!")
        UserProfile.objects.create(user=other, role="tenant")
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        UAEIDVerification.objects.create(user=other, id_hash="def", status="approved")
        from roommates.models import RoommateProfile

        RoommateProfile.objects.create(user=other, bio="Looking", is_looking=True)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/roommates/interest/",
            {
                "to_user_id": other.id,
                "message": "Hi!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_interests(self):
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/roommates/interests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_accept_interest(self):
        other = User.objects.create_user(
            email="other2@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=other, role="tenant")
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        UAEIDVerification.objects.create(user=other, id_hash="def", status="approved")
        from roommates.models import RoommateProfile, RoommateInterest

        RoommateProfile.objects.create(user=self.user, bio="Looking", is_looking=True)
        interest = RoommateInterest.objects.create(
            from_user=other, to_user=self.user, message="Hi"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/roommates/interests/{interest.id}/",
            {"status": "accepted"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        interest.refresh_from_db()
        self.assertEqual(interest.status, "accepted")

    def test_student_can_get_roommate_profile(self):
        student = User.objects.create_user(
            email="student@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=student, role="student")
        self.client.force_authenticate(user=student)
        response = self.client.get("/api/roommates/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data)

    def test_patch_profile_rejects_budget_max_below_existing_min(self):
        from roommates.models import RoommateProfile

        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        RoommateProfile.objects.create(
            user=self.user, bio="x", budget_min=5000, budget_max=8000
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            "/api/roommates/profile/", {"budget_max": 1000}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("budget_max", response.data)

    def test_search_accepts_area_slug_or_id(self):
        other = User.objects.create_user(email="slug@example.com", password="Pass123!")
        UserProfile.objects.create(user=other, role="tenant")
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        UAEIDVerification.objects.create(user=other, id_hash="def", status="approved")
        from roommates.models import RoommateProfile

        RoommateProfile.objects.create(user=other, bio="A", is_looking=True)
        other.roommate_profile.preferred_areas.add(self.area)
        self.client.force_authenticate(user=self.user)
        r_slug = self.client.get("/api/roommates/search/?area=dubai-marina")
        self.assertEqual(len(r_slug.data), 1)
        r_id = self.client.get(f"/api/roommates/search/?area={self.area.id}")
        self.assertEqual(len(r_id.data), 1)

    def test_search_move_in_before_filter(self):
        other = User.objects.create_user(email="move@example.com", password="Pass123!")
        UserProfile.objects.create(user=other, role="tenant")
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        UAEIDVerification.objects.create(user=other, id_hash="def", status="approved")
        from roommates.models import RoommateProfile
        from datetime import date

        RoommateProfile.objects.create(
            user=other,
            bio="B",
            is_looking=True,
            move_in_date=date(2026, 6, 1),
        )
        self.client.force_authenticate(user=self.user)
        r = self.client.get("/api/roommates/search/?move_in_before=2026-05-01")
        self.assertEqual(len(r.data), 0)
        r2 = self.client.get("/api/roommates/search/?move_in_before=2026-12-01")
        self.assertEqual(len(r2.data), 1)

    def test_patch_interest_invalid_status_returns_400(self):
        other = User.objects.create_user(
            email="badstatus@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=other, role="tenant")
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        UAEIDVerification.objects.create(user=other, id_hash="def", status="approved")
        from roommates.models import RoommateProfile, RoommateInterest

        RoommateProfile.objects.create(user=self.user, bio="Looking", is_looking=True)
        interest = RoommateInterest.objects.create(
            from_user=other, to_user=self.user, message="Hi"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/roommates/interests/{interest.id}/",
            {"status": "pending"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_interest_non_recipient_forbidden(self):
        other = User.objects.create_user(
            email="sender@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=other, role="tenant")
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        UAEIDVerification.objects.create(user=other, id_hash="def", status="approved")
        from roommates.models import RoommateProfile, RoommateInterest

        RoommateProfile.objects.create(user=self.user, bio="Looking", is_looking=True)
        interest = RoommateInterest.objects.create(
            from_user=other, to_user=self.user, message="Hi"
        )
        self.client.force_authenticate(user=other)
        response = self.client.patch(
            f"/api/roommates/interests/{interest.id}/",
            {"status": "accepted"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_interest_twice_returns_400(self):
        other = User.objects.create_user(email="twice@example.com", password="Pass123!")
        UserProfile.objects.create(user=other, role="tenant")
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        UAEIDVerification.objects.create(user=other, id_hash="def", status="approved")
        from roommates.models import RoommateProfile, RoommateInterest

        RoommateProfile.objects.create(user=self.user, bio="Looking", is_looking=True)
        interest = RoommateInterest.objects.create(
            from_user=other, to_user=self.user, message="Hi"
        )
        self.client.force_authenticate(user=self.user)
        r1 = self.client.patch(
            f"/api/roommates/interests/{interest.id}/",
            {"status": "accepted"},
            format="json",
        )
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        r2 = self.client.patch(
            f"/api/roommates/interests/{interest.id}/",
            {"status": "declined"},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_interest_returns_400(self):
        other = User.objects.create_user(email="dup@example.com", password="Pass123!")
        UserProfile.objects.create(user=other, role="tenant")
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        UAEIDVerification.objects.create(user=other, id_hash="def", status="approved")
        from roommates.models import RoommateProfile, RoommateInterest

        RoommateProfile.objects.create(user=other, bio="Looking", is_looking=True)
        RoommateInterest.objects.create(
            from_user=self.user, to_user=other, message="First"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/roommates/interest/",
            {"to_user_id": other.id, "message": "Again"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
