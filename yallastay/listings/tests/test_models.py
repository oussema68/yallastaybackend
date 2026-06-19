from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile, LandlordProfile
from core.models import Area
from listings.models import Listing, Favorite

User = get_user_model()


def _landlord():
    user = User.objects.create_user(email="landlord@example.com", password="Pass123!")
    UserProfile.objects.create(user=user, role="landlord")
    LandlordProfile.objects.create(user=user)
    return user


class ListingModelTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.landlord = _landlord()

    def test_create_listing(self):
        listing = Listing.objects.create(
            title="Test Apartment",
            description="Nice place",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=self.landlord,
        )
        self.assertEqual(listing.title, "Test Apartment")
        self.assertEqual(listing.status, "active")
        self.assertEqual(str(listing), "Test Apartment")

    def test_listing_ordering(self):
        Listing.objects.create(
            title="B",
            description="",
            price=3000,
            type="room",
            area=self.area,
            listed_by=self.landlord,
        )
        Listing.objects.create(
            title="A",
            description="",
            price=4000,
            type="studio",
            area=self.area,
            listed_by=self.landlord,
        )
        titles = list(Listing.objects.values_list("title", flat=True))
        self.assertEqual(titles[0], "A")  # -created_at, so newer first


class FavoriteModelTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        landlord = _landlord()
        self.listing = Listing.objects.create(
            title="Test",
            description="",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )

    def test_create_favorite(self):
        fav = Favorite.objects.create(user=self.user, listing=self.listing)
        self.assertEqual(fav.user, self.user)
        self.assertEqual(str(fav), f"{self.user.email} favorited {self.listing.title}")
