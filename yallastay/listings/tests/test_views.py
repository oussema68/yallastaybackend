from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from documents.models import Document
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import (
    UserProfile,
    LandlordProfile,
    RealtorProfile,
    UAEIDVerification,
)
from core.models import Area
from emails.models import EmailMessage
from bookings.models import Reservation
from listings.models import Listing, ListingImage, Favorite
from notifications.models import Notification, NotificationPreference

User = get_user_model()


def _realtor(approved=True):
    user = User.objects.create_user(email="realtor@example.com", password="Pass123!")
    UserProfile.objects.create(user=user, role="realtor")
    rp = RealtorProfile.objects.create(user=user, agency_name="Test Agency")
    rp.is_approved = approved
    rp.save()
    return user


def _landlord():
    user = User.objects.create_user(email="landlord@example.com", password="Pass123!")
    UserProfile.objects.create(user=user, role="landlord")
    LandlordProfile.objects.create(user=user)
    return user


def _tiny_png_upload(name: str) -> SimpleUploadedFile:
    buf = BytesIO()
    Image.new("RGB", (2, 2), color=(100, 120, 140)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def _title_deed_document(user):
    return Document.objects.create(
        user=user,
        document_type="title_deed",
        file=ContentFile(b"%PDF-1.4 test title deed", "title-deed.pdf"),
    )


class ListingViewSetTests(APITestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.user = _landlord()
        self.listing = Listing.objects.create(
            title="Test Apartment",
            description="Nice place",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=self.user,
        )

    def test_list_listings_unauthenticated(self):
        response = self.client.get("/api/listings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_listings_with_filters(self):
        response = self.client.get("/api/listings/?min_price=4000&max_price=6000")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_listing(self):
        response = self.client.get(f"/api/listings/{self.listing.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Test Apartment")

    def test_retrieve_nonexistent_listing(self):
        response = self.client.get("/api/listings/99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_listing_requires_auth(self):
        response = self.client.post(
            "/api/listings/",
            {
                "title": "New",
                "description": "Desc",
                "price": 4000,
                "type": "apartment",
                "area": self.area.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_listing_success(self):
        self.client.force_authenticate(user=self.user)
        deed = _title_deed_document(self.user)
        before_emails = EmailMessage.objects.count()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/listings/",
                {
                    "title": "New Apartment",
                    "description": "Great view",
                    "price": 6000,
                    "type": "apartment",
                    "area": self.area.id,
                    "title_deed_document": deed.id,
                    "title_deed_reference": "Plot 1 / Unit 101 - matches deed",
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "New Apartment")
        self.assertEqual(response.data["trakheesi_permit_number"], "")
        self.assertEqual(Listing.objects.filter(listed_by=self.user).count(), 2)
        self.assertEqual(EmailMessage.objects.count(), before_emails + 1)
        last = EmailMessage.objects.latest("id")
        self.assertEqual(last.template_key, "listing_created")
        n = Notification.objects.filter(
            user=self.user, notification_type="listing"
        ).latest("id")
        self.assertEqual(n.title, "New listing added")
        self.assertIn("New Apartment", n.body)

    def test_create_listing_with_assigned_realtor(self):
        realtor_user = _realtor(approved=True)
        self.client.force_authenticate(user=self.user)
        deed = _title_deed_document(self.user)
        response = self.client.post(
            "/api/listings/",
            {
                "title": "With realtor",
                "description": "Great view",
                "price": 6000,
                "type": "apartment",
                "area": self.area.id,
                "title_deed_document": deed.id,
                "title_deed_reference": "Plot 1 / Unit 101 - matches deed",
                "assigned_realtor": realtor_user.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["assigned_realtor"], realtor_user.id)
        self.assertEqual(
            response.data["assigned_realtor_detail"]["user_id"], realtor_user.id
        )
        self.assertEqual(
            response.data["assigned_realtor_detail"]["agency_name"], "Test Agency"
        )

    def test_create_listing_rejects_unapproved_assigned_realtor(self):
        unapproved = _realtor(approved=False)
        self.client.force_authenticate(user=self.user)
        deed = _title_deed_document(self.user)
        response = self.client.post(
            "/api/listings/",
            {
                "title": "Bad realtor",
                "description": "x",
                "price": 6000,
                "type": "apartment",
                "area": self.area.id,
                "title_deed_document": deed.id,
                "title_deed_reference": "Ref X",
                "assigned_realtor": unapproved.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("assigned_realtor", response.data)

    def test_patch_listing_clears_assigned_realtor(self):
        realtor_user = _realtor(approved=True)
        self.listing.assigned_realtor = realtor_user
        self.listing.save(update_fields=["assigned_realtor"])
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/listings/{self.listing.id}/",
            {"assigned_realtor": None},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data.get("assigned_realtor"))
        self.listing.refresh_from_db()
        self.assertIsNone(self.listing.assigned_realtor_id)

    def test_create_first_listing_uses_first_template(self):
        user = User.objects.create_user(
            email="onlyone@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=user, role="landlord")
        LandlordProfile.objects.create(user=user)
        self.client.force_authenticate(user=user)
        deed = _title_deed_document(user)
        before = EmailMessage.objects.count()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/listings/",
                {
                    "title": "My first place",
                    "description": "Hi",
                    "price": 3000,
                    "type": "studio",
                    "area": self.area.id,
                    "title_deed_document": deed.id,
                    "title_deed_reference": "Title deed ref A",
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Listing.objects.filter(listed_by=user).count(), 1)
        self.assertEqual(EmailMessage.objects.count(), before + 1)
        last = EmailMessage.objects.latest("id")
        self.assertEqual(last.template_key, "listing_created_first")
        self.assertEqual(last.to_email, user.email)
        n = Notification.objects.filter(user=user, notification_type="listing").latest(
            "id"
        )
        self.assertEqual(n.title, "Your first listing is live")
        self.assertIn("My first place", n.body)

    def test_create_listing_skips_in_app_when_disabled(self):
        NotificationPreference.objects.create(
            user=self.user,
            channel="in_app",
            notification_type="listing",
            enabled=False,
        )
        self.client.force_authenticate(user=self.user)
        before_n = Notification.objects.filter(
            user=self.user, notification_type="listing"
        ).count()
        before_e = EmailMessage.objects.count()
        deed = _title_deed_document(self.user)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/listings/",
                {
                    "title": "No bell",
                    "description": "x",
                    "price": 7000,
                    "type": "apartment",
                    "area": self.area.id,
                    "title_deed_document": deed.id,
                    "title_deed_reference": "Ref B",
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Notification.objects.filter(
                user=self.user, notification_type="listing"
            ).count(),
            before_n,
        )
        self.assertEqual(EmailMessage.objects.count(), before_e + 1)

    def test_create_listing_landlord_allows_empty_trakheesi(self):
        self.client.force_authenticate(user=self.user)
        deed = _title_deed_document(self.user)
        response = self.client.post(
            "/api/listings/",
            {
                "title": "No permit yet",
                "description": "x",
                "price": 6000,
                "type": "apartment",
                "area": self.area.id,
                "title_deed_document": deed.id,
                "title_deed_reference": "Ref deed only",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get("trakheesi_permit_number"), "")

    def test_create_listing_landlord_cannot_submit_trakheesi(self):
        self.client.force_authenticate(user=self.user)
        deed = _title_deed_document(self.user)
        response = self.client.post(
            "/api/listings/",
            {
                "title": "Owner permit",
                "description": "x",
                "price": 6000,
                "type": "apartment",
                "area": self.area.id,
                "trakheesi_permit_number": "1234567890",
                "title_deed_document": deed.id,
                "title_deed_reference": "Ref",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("trakheesi_permit_number", response.data)

    def test_create_listing_landlord_requires_title_deed(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/listings/",
            {
                "title": "No deed",
                "description": "x",
                "price": 6000,
                "type": "apartment",
                "area": self.area.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title_deed_document", response.data)

    def test_create_listing_realtor_requires_trakheesi(self):
        realtor = _realtor(approved=True)
        self.client.force_authenticate(user=realtor)
        response = self.client.post(
            "/api/listings/",
            {
                "title": "Broker listing",
                "description": "x",
                "price": 6000,
                "type": "apartment",
                "area": self.area.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("trakheesi_permit_number", response.data)

    def test_create_listing_realtor_success_with_trakheesi(self):
        realtor = _realtor(approved=True)
        self.client.force_authenticate(user=realtor)
        response = self.client.post(
            "/api/listings/",
            {
                "title": "Broker listed",
                "description": "x",
                "price": 6000,
                "type": "apartment",
                "area": self.area.id,
                "trakheesi_permit_number": "1234567890",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["trakheesi_permit_number"], "1234567890")

    def test_create_listing_realtor_rejects_assigned_realtor(self):
        realtor_pub = User.objects.create_user(
            email="pub-rel@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=realtor_pub, role="realtor")
        rp_a = RealtorProfile.objects.create(user=realtor_pub, agency_name="Pub Agency")
        rp_a.is_approved = True
        rp_a.save()
        other = _realtor(approved=True)
        self.client.force_authenticate(user=realtor_pub)
        response = self.client.post(
            "/api/listings/",
            {
                "title": "Bad assign",
                "description": "x",
                "price": 6000,
                "type": "apartment",
                "area": self.area.id,
                "trakheesi_permit_number": "1234567890",
                "assigned_realtor": other.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("assigned_realtor", response.data)

    def test_realtor_lister_can_clear_assigned_realtor_with_null(self):
        realtor_pub = User.objects.create_user(
            email="pub-clear@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=realtor_pub, role="realtor")
        rp_a = RealtorProfile.objects.create(user=realtor_pub, agency_name="Pub Clear")
        rp_a.is_approved = True
        rp_a.save()
        other = _realtor(approved=True)
        listing = Listing.objects.create(
            title="Had wrong broker",
            description="x",
            price=4000,
            type="apartment",
            area=self.area,
            listed_by=realtor_pub,
            trakheesi_permit_number="1234567890",
            assigned_realtor=other,
        )
        self.client.force_authenticate(user=realtor_pub)
        r = self.client.patch(
            f"/api/listings/{listing.id}/",
            {"assigned_realtor": None},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIsNone(r.data.get("assigned_realtor"))

    def test_realtor_lister_cannot_set_assigned_realtor_on_patch(self):
        realtor_pub = User.objects.create_user(
            email="pub-noassign@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=realtor_pub, role="realtor")
        rp_a = RealtorProfile.objects.create(user=realtor_pub, agency_name="Pub")
        rp_a.is_approved = True
        rp_a.save()
        other = _realtor(approved=True)
        listing = Listing.objects.create(
            title="No assign patch",
            description="x",
            price=4000,
            type="apartment",
            area=self.area,
            listed_by=realtor_pub,
            trakheesi_permit_number="1234567890",
        )
        self.client.force_authenticate(user=realtor_pub)
        r = self.client.patch(
            f"/api/listings/{listing.id}/",
            {"assigned_realtor": other.id},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("assigned_realtor", r.data)

    def test_create_listing_with_images_multipart(self):
        self.client.force_authenticate(user=self.user)
        deed = _title_deed_document(self.user)
        f1 = _tiny_png_upload("a.png")
        f2 = _tiny_png_upload("b.png")
        response = self.client.post(
            "/api/listings/",
            {
                "title": "With photos",
                "description": "d",
                "price": "6000",
                "type": "apartment",
                "area": str(self.area.id),
                "title_deed_document": str(deed.id),
                "title_deed_reference": "Ref C",
                "images": [f1, f2],
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data.get("images", [])), 2)
        lid = response.data["id"]
        self.assertEqual(ListingImage.objects.filter(listing_id=lid).count(), 2)

    def test_create_listing_rejects_more_than_30_images(self):
        self.client.force_authenticate(user=self.user)
        deed = _title_deed_document(self.user)
        files = [_tiny_png_upload(f"{i}.png") for i in range(31)]
        response = self.client.post(
            "/api/listings/",
            {
                "title": "Too many",
                "description": "d",
                "price": "6000",
                "type": "apartment",
                "area": str(self.area.id),
                "title_deed_document": str(deed.id),
                "title_deed_reference": "Ref D",
                "images": files,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_listing(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/listings/{self.listing.id}/",
            {
                "price": 5500,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.price, 5500)

    def test_assigned_realtor_can_patch_trakheesi_only(self):
        realtor_user = _realtor(approved=True)
        self.listing.assigned_realtor = realtor_user
        self.listing.save(update_fields=["assigned_realtor"])
        self.client.force_authenticate(user=realtor_user)
        r = self.client.patch(
            f"/api/listings/{self.listing.id}/",
            {"trakheesi_permit_number": "9876543210"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["trakheesi_permit_number"], "9876543210")
        r2 = self.client.patch(
            f"/api/listings/{self.listing.id}/",
            {"price": 1},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_landlord_cannot_patch_trakheesi(self):
        self.client.force_authenticate(user=self.user)
        r = self.client.patch(
            f"/api/listings/{self.listing.id}/",
            {"trakheesi_permit_number": "1111111111"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("trakheesi_permit_number", r.data)

    def test_patch_appends_images_multipart(self):
        self.client.force_authenticate(user=self.user)
        ListingImage.objects.create(
            listing=self.listing, order=0, image=_tiny_png_upload("x.png")
        )
        f1 = _tiny_png_upload("add1.png")
        f2 = _tiny_png_upload("add2.png")
        response = self.client.patch(
            f"/api/listings/{self.listing.id}/",
            {
                "title": "Updated title",
                "images": [f1, f2],
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("images", [])), 3)
        self.assertEqual(ListingImage.objects.filter(listing=self.listing).count(), 3)

    def test_delete_listing_image_owner(self):
        self.client.force_authenticate(user=self.user)
        img = ListingImage.objects.create(
            listing=self.listing, order=0, image=_tiny_png_upload("del.png")
        )
        r = self.client.delete(f"/api/listings/{self.listing.id}/images/{img.id}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ListingImage.objects.filter(pk=img.pk).exists())

    def test_delete_listing_image_non_owner_forbidden(self):
        img = ListingImage.objects.create(
            listing=self.listing, order=0, image=_tiny_png_upload("z.png")
        )
        other = User.objects.create_user(
            email="other2@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=other, role="landlord")
        LandlordProfile.objects.create(user=other)
        self.client.force_authenticate(user=other)
        r = self.client.delete(f"/api/listings/{self.listing.id}/images/{img.id}/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_listing(self):
        self.client.force_authenticate(user=self.user)
        pk = self.listing.id
        response = self.client.delete(f"/api/listings/{pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Listing.objects.filter(pk=pk).exists())

    def test_unapproved_realtor_cannot_create_listing(self):
        realtor = _realtor(approved=False)
        self.client.force_authenticate(user=realtor)
        response = self.client.post(
            "/api/listings/",
            {
                "title": "New",
                "description": "Desc",
                "price": 4000,
                "type": "apartment",
                "area": self.area.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_owner_cannot_update_listing(self):
        other = User.objects.create_user(email="other@example.com", password="Pass123!")
        UserProfile.objects.create(user=other, role="landlord")
        LandlordProfile.objects.create(user=other)
        self.client.force_authenticate(user=other)
        response = self.client.patch(
            f"/api/listings/{self.listing.id}/", {"price": 9999}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_listings_search(self):
        response = self.client.get("/api/listings/?search=Test")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_listings_ordering(self):
        response = self.client.get("/api/listings/?ordering=price")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_listing_interested_only_listed_by(self):
        student = User.objects.create_user(
            email="student@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=student, role="tenant")
        Favorite.objects.create(user=student, listing=self.listing)
        self.client.force_authenticate(user=student)
        r = self.client.get(f"/api/listings/{self.listing.id}/interested/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=self.user)
        r = self.client.get(f"/api/listings/{self.listing.id}/interested/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]["user"]["email"], student.email)

    def test_public_list_excludes_leased(self):
        self.listing.leased = True
        self.listing.save(update_fields=["leased"])
        response = self.client.get("/api/listings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        rows = data.get("results") if isinstance(data, dict) else data
        ids = [x["id"] for x in rows]
        self.assertNotIn(self.listing.id, ids)

    def test_public_list_excludes_completed_lease_signing_if_leased_flag_cleared(self):
        """Browse must hide fully signed leases even if leased was reset (stale data)."""
        from esign.models import LeaseSigningSession

        renter = User.objects.create_user(
            email="signed-renter@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=renter, role="tenant")
        reservation = Reservation.objects.create(
            listing=self.listing,
            user=renter,
            start_date="2026-06-01",
            end_date="2027-05-31",
            status="completed",
        )
        LeaseSigningSession.objects.create(
            reservation=reservation,
            renter_token="pubtest-renter-token-unique-aa",
            lister_token="pubtest-lister-token-unique-bb",
            status="completed",
        )
        Listing.objects.filter(pk=self.listing.pk).update(leased=False)
        response = self.client.get("/api/listings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = (
            response.data.get("results")
            if isinstance(response.data, dict)
            else response.data
        )
        ids = [x["id"] for x in rows]
        self.assertNotIn(self.listing.id, ids)

    def test_mine_includes_leased(self):
        self.listing.leased = True
        self.listing.save(update_fields=["leased"])
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/listings/?mine=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        rows = data.get("results") if isinstance(data, dict) else data
        ids = [x["id"] for x in rows]
        self.assertIn(self.listing.id, ids)
        self.assertTrue(
            any(x.get("leased") for x in rows if x["id"] == self.listing.id)
        )

    def test_mine_includes_property_owner_for_landlord(self):
        """Landlord sees realtor-created listings where they are property_owner."""
        realtor = User.objects.create_user(
            email="realtor-mine-po@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=realtor, role="realtor")
        rp = RealtorProfile.objects.create(user=realtor, agency_name="Test Agency")
        rp.is_approved = True
        rp.save()
        shared = Listing.objects.create(
            title="Realtor-listed unit",
            description="Owner linked",
            price=4000,
            type="apartment",
            area=self.area,
            listed_by=realtor,
            property_owner=self.user,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/listings/?mine=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        rows = data.get("results") if isinstance(data, dict) else data
        ids = [x["id"] for x in rows]
        self.assertIn(shared.id, ids)
        shared_row = next(x for x in rows if x["id"] == shared.id)
        self.assertFalse(shared_row.get("viewer_is_lister"))
        self.assertTrue(shared_row.get("viewer_is_property_owner_only"))
        own_row = next(x for x in rows if x["id"] == self.listing.id)
        self.assertTrue(own_row.get("viewer_is_lister"))
        self.assertFalse(own_row.get("viewer_is_property_owner_only"))

    def test_mine_includes_assigned_realtor_listings(self):
        """Realtor sees landlord-created listings where they are assigned_realtor."""
        realtor = User.objects.create_user(
            email="realtor-assigned-mine@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=realtor, role="realtor")
        rp = RealtorProfile.objects.create(user=realtor, agency_name="Assist Agency")
        rp.is_approved = True
        rp.save()
        owner_listing = Listing.objects.create(
            title="Owner-listed with broker",
            description="Photos by owner",
            price=4500,
            type="apartment",
            area=self.area,
            listed_by=self.user,
            assigned_realtor=realtor,
        )
        self.client.force_authenticate(user=realtor)
        response = self.client.get("/api/listings/?mine=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        rows = data.get("results") if isinstance(data, dict) else data
        ids = [x["id"] for x in rows]
        self.assertIn(owner_listing.id, ids)

    def test_anonymous_cannot_retrieve_leased(self):
        self.listing.leased = True
        self.listing.save(update_fields=["leased"])
        response = self.client.get(f"/api/listings/{self.listing.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_renter_with_reservation_can_retrieve_leased(self):
        renter = User.objects.create_user(
            email="tenant@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=renter, role="tenant")
        Reservation.objects.create(
            listing=self.listing,
            user=renter,
            start_date="2026-06-01",
            end_date="2027-05-31",
            status="pending",
        )
        self.listing.leased = True
        self.listing.save(update_fields=["leased"])
        self.client.force_authenticate(user=renter)
        response = self.client.get(f"/api/listings/{self.listing.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("leased"))

    def test_other_user_cannot_retrieve_leased(self):
        other = User.objects.create_user(
            email="stranger@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=other, role="tenant")
        self.listing.leased = True
        self.listing.save(update_fields=["leased"])
        self.client.force_authenticate(user=other)
        response = self.client.get(f"/api/listings/{self.listing.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_verification_request_and_approve(self):
        realtor = User.objects.create_user(
            email="rel-ov1@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=realtor, role="realtor")
        rp = RealtorProfile.objects.create(user=realtor, agency_name="Agency OV")
        rp.is_approved = True
        rp.save()
        owner = User.objects.create_user(
            email="owner-ov1@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=owner, role="landlord")
        LandlordProfile.objects.create(user=owner)
        UAEIDVerification.objects.create(
            user=owner, id_hash="b" * 64, status="approved"
        )
        deed = Document.objects.create(
            user=owner,
            document_type="title_deed",
            file=ContentFile(b"%PDF-1.4 deed", "deed.pdf"),
        )
        listing = Listing.objects.create(
            title="Broker listed for owner",
            description="x",
            price=4000,
            type="apartment",
            area=self.area,
            listed_by=realtor,
            property_owner=owner,
            assigned_realtor=realtor,
            title_deed_document=deed,
            title_deed_reference="Ref OV1",
            trakheesi_permit_number="1234567890",
        )
        self.client.force_authenticate(user=owner)
        r = self.client.post(f"/api/listings/{listing.id}/request-owner-verification/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["owner_verification_status"], "pending")

        self.client.force_authenticate(user=realtor)
        r2 = self.client.post(
            f"/api/listings/{listing.id}/approve-owner-verification/",
            {"note": "Documents conform."},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.data["owner_verification_status"], "approved")

    def test_owner_verification_reject(self):
        realtor = User.objects.create_user(
            email="rel-ov3@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=realtor, role="realtor")
        rp = RealtorProfile.objects.create(user=realtor, agency_name="Agency OV3")
        rp.is_approved = True
        rp.save()
        owner = User.objects.create_user(
            email="owner-ov3@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=owner, role="landlord")
        LandlordProfile.objects.create(user=owner)
        UAEIDVerification.objects.create(
            user=owner, id_hash="d" * 64, status="approved"
        )
        deed = Document.objects.create(
            user=owner,
            document_type="title_deed",
            file=ContentFile(b"%PDF-1.4 deed", "deed3.pdf"),
        )
        listing = Listing.objects.create(
            title="Reject flow",
            description="x",
            price=4000,
            type="apartment",
            area=self.area,
            listed_by=realtor,
            property_owner=owner,
            assigned_realtor=realtor,
            title_deed_document=deed,
            title_deed_reference="Ref",
            trakheesi_permit_number="1234567890",
        )
        self.client.force_authenticate(user=owner)
        self.client.post(f"/api/listings/{listing.id}/request-owner-verification/")
        self.client.force_authenticate(user=realtor)
        r_short = self.client.post(
            f"/api/listings/{listing.id}/reject-owner-verification/",
            {"reason": "bad"},
            format="json",
        )
        self.assertEqual(r_short.status_code, status.HTTP_400_BAD_REQUEST)
        r_ok = self.client.post(
            f"/api/listings/{listing.id}/reject-owner-verification/",
            {
                "reason": "Title deed name does not match the account; please upload a matching deed."
            },
            format="json",
        )
        self.assertEqual(r_ok.status_code, status.HTTP_200_OK)
        self.assertEqual(r_ok.data["owner_verification_status"], "rejected")

    def test_property_owner_can_patch_title_deed_only(self):
        realtor = User.objects.create_user(
            email="rel-po@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=realtor, role="realtor")
        rp = RealtorProfile.objects.create(user=realtor, agency_name="PO")
        rp.is_approved = True
        rp.save()
        owner = User.objects.create_user(
            email="owner-po@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=owner, role="landlord")
        LandlordProfile.objects.create(user=owner)
        deed = Document.objects.create(
            user=owner,
            document_type="title_deed",
            file=ContentFile(b"%PDF-1.4 deed", "po-deed.pdf"),
        )
        listing = Listing.objects.create(
            title="PO",
            description="x",
            price=4000,
            type="apartment",
            area=self.area,
            listed_by=realtor,
            property_owner=owner,
            title_deed_document=None,
            title_deed_reference="",
            trakheesi_permit_number="1234567890",
        )
        self.client.force_authenticate(user=owner)
        r = self.client.patch(
            f"/api/listings/{listing.id}/",
            {"title_deed_document": deed.id, "title_deed_reference": "Plot 9"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["title_deed_reference"], "Plot 9")
        r2 = self.client.patch(
            f"/api/listings/{listing.id}/",
            {"price": 1},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)


class FavoriteViewSetTests(APITestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        landlord = _landlord()
        self.listing = Listing.objects.create(
            title="Test",
            description="Desc",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )

    def test_list_favorites_requires_auth(self):
        response = self.client.get("/api/favorites/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_favorite(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/favorites/", {"listing": self.listing.id}, format="json"
        )
        self.assertIn(
            response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED)
        )
        self.assertTrue(
            Favorite.objects.filter(user=self.user, listing=self.listing).exists()
        )

    def test_remove_favorite(self):
        fav = Favorite.objects.create(user=self.user, listing=self.listing)
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f"/api/favorites/{fav.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Favorite.objects.filter(pk=fav.id).exists())
