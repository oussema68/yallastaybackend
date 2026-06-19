from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile, LandlordProfile
from core.models import Area
from listings.models import Listing
from reviews.models import Review, ReviewResponse

User = get_user_model()


def _landlord():
    user = User.objects.create_user(email="landlord@example.com", password="Pass123!")
    UserProfile.objects.create(user=user, role="landlord")
    LandlordProfile.objects.create(user=user)
    return user


class ReviewModelTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.reviewer = User.objects.create_user(
            email="reviewer@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.reviewer, role="tenant")
        landlord = _landlord()
        self.listing = Listing.objects.create(
            title="Test",
            description="",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )

    def test_create_review(self):
        rev = Review.objects.create(
            reviewer=self.reviewer,
            reviewee=self.listing.listed_by,
            listing=self.listing,
            rating=5,
            comment="Great!",
        )
        self.assertEqual(rev.rating, 5)
        self.assertEqual(
            str(rev), f"{self.reviewer.email} → {self.listing.listed_by.email} (5★)"
        )


class ReviewResponseModelTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.reviewer = User.objects.create_user(
            email="reviewer@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.reviewer, role="tenant")
        landlord = _landlord()
        self.listing = Listing.objects.create(
            title="Test",
            description="",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )
        self.review = Review.objects.create(
            reviewer=self.reviewer,
            reviewee=landlord,
            listing=self.listing,
            rating=5,
            comment="Great!",
        )

    def test_create_response(self):
        resp = ReviewResponse.objects.create(
            review=self.review, response_text="Thanks!"
        )
        self.assertEqual(resp.response_text, "Thanks!")
