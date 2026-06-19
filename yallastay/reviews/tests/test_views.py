from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import UserProfile, LandlordProfile, UAEIDVerification
from core.models import Area
from listings.models import Listing
from reviews.models import Review, ReviewResponse

User = get_user_model()


def _landlord():
    user = User.objects.create_user(email="landlord@example.com", password="Pass123!")
    UserProfile.objects.create(user=user, role="landlord")
    LandlordProfile.objects.create(user=user)
    return user


class ReviewViewTests(APITestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.reviewer = User.objects.create_user(
            email="reviewer@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.reviewer, role="tenant")
        self.reviewee = User.objects.create_user(
            email="reviewee@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.reviewee, role="tenant")
        landlord = _landlord()
        self.listing = Listing.objects.create(
            title="Test",
            description="Desc",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )

    def test_list_reviews_requires_auth(self):
        response = self.client.get("/api/reviews/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_reviews_authenticated(self):
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.get("/api/reviews/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_list_reviews_filter_by_user(self):
        Review.objects.create(
            reviewer=self.reviewer,
            reviewee=self.reviewee,
            listing=self.listing,
            rating=5,
            comment="Great!",
        )
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.get(f"/api/reviews/?user={self.reviewee.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_review_without_uae_id_returns_403(self):
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.post(
            "/api/reviews/",
            {
                "reviewee_id": self.reviewee.id,
                "listing_id": self.listing.id,
                "rating": 5,
                "comment": "Great!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_review_with_uae_id(self):
        UAEIDVerification.objects.create(
            user=self.reviewer, id_hash="abc", status="approved"
        )
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.post(
            "/api/reviews/",
            {
                "reviewee_id": self.reviewee.id,
                "listing_id": self.listing.id,
                "rating": 5,
                "comment": "Great landlord!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["rating"], 5)
        self.assertTrue(
            Review.objects.filter(
                reviewer=self.reviewer, reviewee=self.reviewee
            ).exists()
        )

    def test_create_review_invalid_rating(self):
        UAEIDVerification.objects.create(
            user=self.reviewer, id_hash="abc", status="approved"
        )
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.post(
            "/api/reviews/",
            {
                "reviewee_id": self.reviewee.id,
                "listing_id": self.listing.id,
                "rating": 10,  # Invalid: max 5
                "comment": "Great!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_review_response_only_reviewee(self):
        rev = Review.objects.create(
            reviewer=self.reviewer,
            reviewee=self.reviewee,
            listing=self.listing,
            rating=5,
            comment="Great!",
        )
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.post(
            f"/api/reviews/{rev.id}/response/",
            {
                "response_text": "Thanks!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_review_response_as_reviewee(self):
        rev = Review.objects.create(
            reviewer=self.reviewer,
            reviewee=self.reviewee,
            listing=self.listing,
            rating=5,
            comment="Great!",
        )
        self.client.force_authenticate(user=self.reviewee)
        response = self.client.post(
            f"/api/reviews/{rev.id}/response/",
            {
                "response_text": "Thanks for the feedback!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ReviewResponse.objects.filter(review=rev).exists())

    def test_list_reviews_filter_by_listing(self):
        Review.objects.create(
            reviewer=self.reviewer,
            reviewee=self.reviewee,
            listing=self.listing,
            rating=5,
            comment="Great!",
        )
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.get(f"/api/reviews/?listing={self.listing.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_review_detail(self):
        rev = Review.objects.create(
            reviewer=self.reviewer,
            reviewee=self.reviewee,
            listing=self.listing,
            rating=5,
            comment="Great!",
        )
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.get(f"/api/reviews/{rev.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_review_cannot_review_self(self):
        UAEIDVerification.objects.create(
            user=self.reviewer, id_hash="abc", status="approved"
        )
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.post(
            "/api/reviews/",
            {
                "reviewee_id": self.reviewer.id,
                "listing_id": self.listing.id,
                "rating": 5,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_review_response_already_exists_returns_400(self):
        rev = Review.objects.create(
            reviewer=self.reviewer,
            reviewee=self.reviewee,
            listing=self.listing,
            rating=5,
            comment="Great!",
        )
        ReviewResponse.objects.create(review=rev, response_text="Already replied")
        self.client.force_authenticate(user=self.reviewee)
        response = self.client.post(
            f"/api/reviews/{rev.id}/response/",
            {
                "response_text": "Second reply",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
