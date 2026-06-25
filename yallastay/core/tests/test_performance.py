"""Tests for listing image compression and account overview batch endpoint."""

from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import LandlordProfile, UserProfile
from core.image_processing import prepare_listing_image_upload
from core.models import StoredMedia
from listings.models import Listing

User = get_user_model()


def _large_jpeg_upload(name: str = "huge.jpg") -> SimpleUploadedFile:
    buf = BytesIO()
    Image.new("RGB", (4000, 3000), color=(200, 100, 50)).save(
        buf, format="JPEG", quality=95
    )
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


class ImageProcessingTests(APITestCase):
    def test_prepare_listing_image_upload_shrinks_large_files(self):
        upload = _large_jpeg_upload()
        main, thumb = prepare_listing_image_upload(upload)
        self.assertLess(len(main.read()), 900_000)
        self.assertLess(len(thumb.read()), 200_000)

    def test_create_listing_image_stores_thumbnail(self):
        user = User.objects.create_user(email="img@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="realtor")
        listing = Listing.objects.create(
            title="Photo test",
            price=5000,
            type="studio",
            listed_by=user,
            trakheesi_permit_number="1234567890",
        )
        from listings.images import create_listing_image

        img = create_listing_image(listing, _large_jpeg_upload(), order=0)
        self.assertTrue(img.image.name)
        self.assertTrue(img.thumbnail.name)
        self.assertTrue(StoredMedia.objects.filter(name=img.image.name).exists())
        self.assertTrue(StoredMedia.objects.filter(name=img.thumbnail.name).exists())


class AccountOverviewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="dash@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="landlord")
        LandlordProfile.objects.create(user=self.user, is_approved=True)

    def test_account_overview_returns_user_and_badges(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/auth/account-overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], self.user.email)
        self.assertIn("verification", response.data)
        self.assertIn("unread_messages", response.data)
        self.assertIn("unread_notifications", response.data)
        self.assertIn("reservations", response.data)
        self.assertIn("my_listings", response.data)
