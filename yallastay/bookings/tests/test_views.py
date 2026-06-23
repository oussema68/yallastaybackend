from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import UserProfile, LandlordProfile, UAEIDVerification
from core.models import Area
from listings.models import Listing
from bookings.models import ViewingRequest, Reservation
from payments.models import Payment

User = get_user_model()


def _landlord():
    user = User.objects.create_user(email="landlord@example.com", password="Pass123!")
    UserProfile.objects.create(user=user, role="landlord")
    LandlordProfile.objects.create(user=user)
    return user


def _lease_start_end(start_days_ahead=7):
    """Reservation rules: start_date is 2-15 days from today; end after start."""
    today = timezone.now().date()
    start = today + timedelta(days=start_days_ahead)
    end = start + timedelta(days=30)
    return start, end


class BookingsViewTests(APITestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.landlord = _landlord()
        self.tenant = User.objects.create_user(
            email="tenant@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.tenant, role="tenant")
        self.listing = Listing.objects.create(
            title="Test",
            description="Desc",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=self.landlord,
        )

    def test_list_viewings_requires_auth(self):
        response = self.client.get("/api/viewings/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_viewings_as_tenant(self):
        ViewingRequest.objects.create(
            listing=self.listing,
            user=self.tenant,
            requested_datetime="2025-03-01T10:00:00Z",
            status="pending",
        )
        self.client.force_authenticate(user=self.tenant)
        response = self.client.get("/api/viewings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_request_viewing_without_uae_id_returns_403(self):
        self.client.force_authenticate(user=self.tenant)
        response = self.client.post(
            "/api/viewings/",
            {
                "listing_id": self.listing.id,
                "requested_datetime": "2025-03-15T10:00:00Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_request_viewing_with_uae_id(self):
        UAEIDVerification.objects.create(
            user=self.tenant, id_hash="abc123", status="approved"
        )
        self.client.force_authenticate(user=self.tenant)
        response = self.client.post(
            "/api/viewings/",
            {
                "listing_id": self.listing.id,
                "requested_datetime": "2025-03-15T10:00:00Z",
                "notes": "Morning slot",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ViewingRequest.objects.filter(user=self.tenant).count(), 1)

    def test_landlord_confirm_viewing(self):
        viewing = ViewingRequest.objects.create(
            listing=self.listing,
            user=self.tenant,
            requested_datetime="2025-03-01T10:00:00Z",
            status="pending",
        )
        self.client.force_authenticate(user=self.landlord)
        response = self.client.patch(
            f"/api/viewings/{viewing.id}/", {"status": "confirmed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        viewing.refresh_from_db()
        self.assertEqual(viewing.status, "confirmed")

    def test_tenant_cannot_confirm_viewing(self):
        viewing = ViewingRequest.objects.create(
            listing=self.listing,
            user=self.tenant,
            requested_datetime="2025-03-01T10:00:00Z",
            status="pending",
        )
        self.client.force_authenticate(user=self.tenant)
        response = self.client.patch(
            f"/api/viewings/{viewing.id}/", {"status": "confirmed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_viewings_as_landlord(self):
        ViewingRequest.objects.create(
            listing=self.listing,
            user=self.tenant,
            requested_datetime="2025-03-01T10:00:00Z",
            status="pending",
        )
        self.client.force_authenticate(user=self.landlord)
        response = self.client.get("/api/viewings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_reservations_requires_auth(self):
        response = self.client.get("/api/reservations/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_reservation_without_uae_id_returns_403(self):
        start, end = _lease_start_end()
        self.client.force_authenticate(user=self.tenant)
        response = self.client.post(
            "/api/reservations/",
            {
                "listing_id": self.listing.id,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_reservation_with_uae_id(self):
        start, end = _lease_start_end()
        UAEIDVerification.objects.create(
            user=self.tenant, id_hash="abc123", status="approved"
        )
        self.client.force_authenticate(user=self.tenant)
        response = self.client.post(
            "/api/reservations/",
            {
                "listing_id": self.listing.id,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "notes": "Moving in with two cats.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.filter(user=self.tenant).count(), 1)
        res = Reservation.objects.get(user=self.tenant)
        self.assertEqual(res.notes, "Moving in with two cats.")

    def test_rent_from_app_endpoint(self):
        start, end = _lease_start_end()
        UAEIDVerification.objects.create(
            user=self.tenant, id_hash="abc123", status="approved"
        )
        self.client.force_authenticate(user=self.tenant)
        response = self.client.post(
            f"/api/listings/{self.listing.id}/rent/",
            {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.filter(user=self.tenant).count(), 1)

    def test_reservation_rejects_lease_start_before_two_days(self):
        UAEIDVerification.objects.create(
            user=self.tenant, id_hash="abc123", status="approved"
        )
        self.client.force_authenticate(user=self.tenant)
        today = timezone.now().date()
        start = today + timedelta(days=1)
        end = start + timedelta(days=30)
        response = self.client.post(
            "/api/reservations/",
            {
                "listing_id": self.listing.id,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_date", response.data)

    def test_reservation_rejects_lease_start_beyond_fifteen_days(self):
        UAEIDVerification.objects.create(
            user=self.tenant, id_hash="abc123", status="approved"
        )
        self.client.force_authenticate(user=self.tenant)
        today = timezone.now().date()
        start = today + timedelta(days=16)
        end = start + timedelta(days=30)
        response = self.client.post(
            "/api/reservations/",
            {
                "listing_id": self.listing.id,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_date", response.data)

    def test_cannot_rent_own_listing(self):
        own_listing = Listing.objects.create(
            title="Mine",
            description="",
            price=3000,
            type="apartment",
            area=self.area,
            listed_by=self.tenant,
        )
        UAEIDVerification.objects.create(
            user=self.tenant, id_hash="abc456", status="approved"
        )
        start, end = _lease_start_end()
        self.client.force_authenticate(user=self.tenant)
        response = self.client.post(
            "/api/reservations/",
            {
                "listing_id": own_listing.id,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("listing_id", response.data)

    def test_landlord_cannot_create_reservation_as_renter(self):
        other = User.objects.create_user(
            email="other-landlord@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=other, role="landlord")
        LandlordProfile.objects.create(user=other)
        other_listing = Listing.objects.create(
            title="Other",
            description="",
            price=4000,
            type="apartment",
            area=self.area,
            listed_by=other,
        )
        UAEIDVerification.objects.create(
            user=self.landlord, id_hash="landlord_uae", status="approved"
        )
        start, end = _lease_start_end()
        self.client.force_authenticate(user=self.landlord)
        response = self.client.post(
            "/api/reservations/",
            {
                "listing_id": other_listing.id,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_lister_confirms_reservation(self):
        start, end = _lease_start_end()
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.tenant,
            start_date=start,
            end_date=end,
            status="pending",
        )
        self.client.force_authenticate(user=self.landlord)
        response = self.client.patch(
            f"/api/reservations/{res.id}/", {"status": "confirmed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res.refresh_from_db()
        self.assertEqual(res.status, "confirmed")

    def test_renter_cancels_pending_reservation(self):
        start, end = _lease_start_end()
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.tenant,
            start_date=start,
            end_date=end,
            status="pending",
        )
        self.client.force_authenticate(user=self.tenant)
        response = self.client.patch(
            f"/api/reservations/{res.id}/", {"status": "cancelled"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res.refresh_from_db()
        self.assertEqual(res.status, "cancelled")

    def test_cancel_reservation_marks_pending_payments_cancelled(self):
        start, end = _lease_start_end()
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.tenant,
            start_date=start,
            end_date=end,
            status="pending",
        )
        pay = Payment.objects.create(
            user=self.tenant,
            amount=1000,
            currency="AED",
            payment_type="deposit",
            status="pending",
            reservation=res,
        )
        self.client.force_authenticate(user=self.tenant)
        response = self.client.patch(
            f"/api/reservations/{res.id}/", {"status": "cancelled"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pay.refresh_from_db()
        self.assertEqual(pay.status, "cancelled")

    def test_renter_cannot_confirm(self):
        start, end = _lease_start_end()
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.tenant,
            start_date=start,
            end_date=end,
            status="pending",
        )
        self.client.force_authenticate(user=self.tenant)
        response = self.client.patch(
            f"/api/reservations/{res.id}/", {"status": "confirmed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_reservation_as_tenant(self):
        start, end = _lease_start_end()
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.tenant,
            start_date=start,
            end_date=end,
            status="pending",
        )
        self.client.force_authenticate(user=self.tenant)
        response = self.client.get(f"/api/reservations/{res.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_landlord_reject_viewing(self):
        viewing = ViewingRequest.objects.create(
            listing=self.listing,
            user=self.tenant,
            requested_datetime="2025-03-01T10:00:00Z",
            status="pending",
        )
        self.client.force_authenticate(user=self.landlord)
        response = self.client.patch(
            f"/api/viewings/{viewing.id}/", {"status": "rejected"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        viewing.refresh_from_db()
        self.assertEqual(viewing.status, "rejected")

    def test_landlord_retrieve_reservation(self):
        start, end = _lease_start_end()
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.tenant,
            start_date=start,
            end_date=end,
            status="pending",
        )
        self.client.force_authenticate(user=self.landlord)
        response = self.client.get(f"/api/reservations/{res.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_move_in_patch_renter_confirms_keys_and_feedback(self):
        start, end = _lease_start_end()
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.tenant,
            start_date=start,
            end_date=end,
            status="confirmed",
        )
        self.client.force_authenticate(user=self.tenant)
        r = self.client.patch(
            f"/api/reservations/{res.id}/move-in/",
            {"keys_received": True, "platform_feedback": "Smooth so far."},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertTrue(r.data.get("keys_received"))
        self.assertIsNotNone(r.data.get("keys_received_at"))
        self.assertEqual(r.data.get("platform_feedback"), "Smooth so far.")
        self.assertIsInstance(r.data.get("move_in_guidance"), dict)
        res.refresh_from_db()
        self.assertIsNotNone(res.keys_received_at)

    def test_move_in_lister_gets_null_guidance_and_feedback(self):
        start, end = _lease_start_end()
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.tenant,
            start_date=start,
            end_date=end,
            status="confirmed",
            platform_feedback="Secret",
        )
        self.client.force_authenticate(user=self.landlord)
        r = self.client.get(f"/api/reservations/{res.id}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIsNone(r.data.get("move_in_guidance"))
        self.assertEqual(r.data.get("platform_feedback"), "")
        self.assertIsNone(r.data.get("keys_received_at"))

    def test_move_in_forbidden_for_pending(self):
        start, end = _lease_start_end()
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.tenant,
            start_date=start,
            end_date=end,
            status="pending",
        )
        self.client.force_authenticate(user=self.tenant)
        r = self.client.patch(
            f"/api/reservations/{res.id}/move-in/",
            {"keys_received": True},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_move_in_lister_cannot_patch(self):
        start, end = _lease_start_end()
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.tenant,
            start_date=start,
            end_date=end,
            status="confirmed",
        )
        self.client.force_authenticate(user=self.landlord)
        r = self.client.patch(
            f"/api/reservations/{res.id}/move-in/",
            {"keys_received": True},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_viewing_detail_as_tenant(self):
        viewing = ViewingRequest.objects.create(
            listing=self.listing,
            user=self.tenant,
            requested_datetime="2025-03-01T10:00:00Z",
            status="pending",
        )
        self.client.force_authenticate(user=self.tenant)
        response = self.client.get(f"/api/viewings/{viewing.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_viewing_detail_missing_returns_404(self):
        self.client.force_authenticate(user=self.tenant)
        response = self.client.get("/api/viewings/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
