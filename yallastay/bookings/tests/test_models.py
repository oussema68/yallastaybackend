from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile, LandlordProfile
from core.models import Area
from listings.models import Listing
from bookings.models import ViewingRequest, Reservation

User = get_user_model()


def _landlord():
    user = User.objects.create_user(email="landlord@example.com", password="Pass123!")
    UserProfile.objects.create(user=user, role="landlord")
    LandlordProfile.objects.create(user=user)
    return user


class ViewingRequestModelTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.landlord = _landlord()
        self.tenant = User.objects.create_user(
            email="tenant@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.tenant, role="tenant")
        self.listing = Listing.objects.create(
            title="Test",
            description="",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=self.landlord,
        )

    def test_create_viewing_request(self):
        vr = ViewingRequest.objects.create(
            listing=self.listing,
            user=self.tenant,
            requested_datetime="2025-03-15T10:00:00Z",
            status="pending",
        )
        self.assertEqual(vr.status, "pending")
        self.assertEqual(vr.listing, self.listing)


class ReservationModelTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.landlord = _landlord()
        self.tenant = User.objects.create_user(
            email="tenant@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.tenant, role="tenant")
        self.listing = Listing.objects.create(
            title="Test",
            description="",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=self.landlord,
        )

    def test_create_reservation(self):
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.tenant,
            start_date="2025-04-01",
            end_date="2025-10-01",
            status="pending",
        )
        self.assertEqual(res.status, "pending")
        self.assertEqual(res.user, self.tenant)
