"""Tests for LeaseSigningSessionSerializer (dashboard API shape)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings

from accounts.models import LandlordProfile, RealtorProfile, UserProfile
from bookings.models import Reservation
from core.models import Area
from listings.models import Listing
from payments.models import Payment

from esign.serializers import LeaseSigningSessionSerializer
from esign.services import after_rental_payment_completed

User = get_user_model()


@override_settings(ESIGN_AUTO_GENERATE_CONTRACT_PDF=True)
class LeaseSigningSessionSerializerTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.area = Area.objects.create(name="S", slug="s")
        self.lister = User.objects.create_user(
            email="ls@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.lister, role="landlord")
        LandlordProfile.objects.create(user=self.lister)
        self.renter = User.objects.create_user(
            email="rs@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.renter, role="tenant")
        self.listing = Listing.objects.create(
            title="Ser",
            description="d",
            price=3200,
            type="apartment",
            area=self.area,
            listed_by=self.lister,
        )
        self.reservation = Reservation.objects.create(
            listing=self.listing,
            user=self.renter,
            start_date="2026-08-01",
            end_date="2027-07-31",
            status="pending",
        )
        p = Payment.objects.create(
            user=self.renter,
            amount=3200,
            payment_type="rent",
            status="completed",
            transaction_id="ys_ser",
            reservation=self.reservation,
        )
        self.session = after_rental_payment_completed(p)

    def _ctx(self, user):
        request = self.factory.get("/api/esign/sessions/")
        request.user = user
        return {"request": request}

    def test_renter_sees_role_contract_ready_and_pdf_path(self):
        ser = LeaseSigningSessionSerializer(
            self.session, context=self._ctx(self.renter)
        )
        d = ser.data
        self.assertEqual(d["viewer_role"], "renter")
        self.assertTrue(d["contract_pdf_ready"])
        self.assertIn("/esign/sign/", d["pdf_api_url"])
        self.assertTrue(d["can_sign"])
        self.assertEqual(d["signing_progress"], "waiting_renter")

    def test_lister_sees_upload_flags_when_pdf_ready(self):
        ser = LeaseSigningSessionSerializer(
            self.session, context=self._ctx(self.lister)
        )
        d = ser.data
        self.assertEqual(d["viewer_role"], "landlord_lister")
        self.assertFalse(d["listing_has_property_owner"])
        self.assertTrue(d["contract_pdf_ready"])
        self.assertFalse(d["needs_lister_contract_upload"])
        self.assertTrue(d["can_upload_contract"])
        self.assertFalse(d["can_sign"])

    def test_realtor_as_signer_sees_realtor_lister(self):
        realtor = User.objects.create_user(email="rt@example.com", password="Pass123!")
        UserProfile.objects.create(user=realtor, role="realtor")
        RealtorProfile.objects.create(
            user=realtor, agency_name="Agency", is_approved=True
        )
        listing = Listing.objects.create(
            title="Realtor listed",
            description="d",
            price=3000,
            type="apartment",
            area=self.area,
            listed_by=realtor,
        )
        reservation = Reservation.objects.create(
            listing=listing,
            user=self.renter,
            start_date="2026-08-01",
            end_date="2027-07-31",
            status="pending",
        )
        p = Payment.objects.create(
            user=self.renter,
            amount=3000,
            payment_type="rent",
            status="completed",
            transaction_id="ys_rt",
            reservation=reservation,
        )
        session = after_rental_payment_completed(p)
        self.assertIsNotNone(session)
        ser = LeaseSigningSessionSerializer(session, context=self._ctx(realtor))
        d = ser.data
        self.assertEqual(d["viewer_role"], "realtor_lister")
        self.assertFalse(d["listing_has_property_owner"])

    def test_unauthenticated_request_returns_null_viewer_fields(self):
        request = self.factory.get("/api/esign/sessions/")
        request.user = AnonymousUser()
        ser = LeaseSigningSessionSerializer(self.session, context={"request": request})
        d = ser.data
        self.assertIsNone(d["viewer_role"])
        self.assertIsNone(d["pdf_api_url"])
        self.assertIsNone(d["my_sign_url"])
