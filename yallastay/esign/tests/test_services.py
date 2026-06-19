import io

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from pypdf import PdfReader

from accounts.models import LandlordProfile, UserProfile
from bookings.models import Reservation
from core.models import Area
from listings.models import Listing
from payments.models import Payment

from esign.models import LeaseSigningSession
from esign.pdf_service import build_contract_pdf_bytes
from esign.services import (
    after_rental_payment_completed,
    preview_sign_token,
    sign_with_token,
)

User = get_user_model()


def sample_signature_png() -> bytes:
    from io import BytesIO

    from PIL import Image, ImageDraw

    buf = BytesIO()
    im = Image.new("RGB", (200, 80), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.line([(10, 40), (190, 40)], fill=(0, 0, 0), width=2)
    im.save(buf, format="PNG")
    return buf.getvalue()


def tiny_invalid_png() -> bytes:
    """PNG bytes under MIN_SIGNATURE_BYTES - must fail validate_signature_png."""
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (32, 32), (255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


@override_settings(ESIGN_AUTO_GENERATE_CONTRACT_PDF=True)
class EsignServiceTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="X", slug="x")
        self.lister = User.objects.create_user(
            email="lister@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.lister, role="landlord")
        LandlordProfile.objects.create(user=self.lister)
        self.renter = User.objects.create_user(
            email="renter@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.renter, role="tenant")
        self.listing = Listing.objects.create(
            title="Apt",
            description="d",
            price=4000,
            type="apartment",
            area=self.area,
            listed_by=self.lister,
        )
        self.reservation = Reservation.objects.create(
            listing=self.listing,
            user=self.renter,
            start_date="2026-05-01",
            end_date="2027-04-30",
            status="pending",
        )

    def test_after_payment_creates_session_once(self):
        p = Payment.objects.create(
            user=self.renter,
            amount=4000,
            payment_type="rent",
            status="completed",
            transaction_id="ys_1",
            reservation=self.reservation,
        )
        s1 = after_rental_payment_completed(p)
        self.assertIsNotNone(s1)
        self.assertEqual(LeaseSigningSession.objects.count(), 1)
        s1.refresh_from_db()
        self.assertTrue(s1.contract_pdf.name)
        self.assertEqual(len(s1.contract_pdf_sha256), 64)
        s2 = after_rental_payment_completed(p)
        self.assertIsNone(s2)
        self.assertEqual(LeaseSigningSession.objects.count(), 1)

    def test_sign_both_completes(self):
        p = Payment.objects.create(
            user=self.renter,
            amount=4000,
            payment_type="deposit",
            status="completed",
            transaction_id="ys_2",
            reservation=self.reservation,
        )
        session = after_rental_payment_completed(p)
        self.assertIsNotNone(session)

        sig = sample_signature_png()
        s, err = sign_with_token(session.renter_token, signature_png_bytes=sig)
        self.assertIsNone(err)
        self.assertEqual(s.status, "pending")
        s.refresh_from_db()
        self.assertIsNotNone(s.renter_signed_at)

        s2, err2 = sign_with_token(session.lister_token, signature_png_bytes=sig)
        self.assertIsNone(err2)
        s2.refresh_from_db()
        self.assertEqual(s2.status, "completed")
        self.assertTrue(s2.signed_pdf.name)
        self.reservation.refresh_from_db()
        self.assertIn("lease_signed_at", self.reservation.dld_metadata)

    def test_sign_rejects_missing_signature_png(self):
        p = Payment.objects.create(
            user=self.renter,
            amount=4000,
            payment_type="rent",
            status="completed",
            transaction_id="ys_sigmiss",
            reservation=self.reservation,
        )
        session = after_rental_payment_completed(p)
        s, err = sign_with_token(session.renter_token, signature_png_bytes=None)
        self.assertIsNone(s)
        self.assertEqual(err, "missing_signature")

    def test_lister_cannot_sign_before_renter(self):
        p = Payment.objects.create(
            user=self.renter,
            amount=4000,
            payment_type="rent",
            status="completed",
            transaction_id="ys_order",
            reservation=self.reservation,
        )
        session = after_rental_payment_completed(p)
        s, err = sign_with_token(
            session.lister_token, signature_png_bytes=sample_signature_png()
        )
        self.assertEqual(err, "renter_must_sign_first")

    def test_preview_renter_can_sign_when_pdf_ready(self):
        p = Payment.objects.create(
            user=self.renter,
            amount=4000,
            payment_type="rent",
            status="completed",
            transaction_id="ys_prev_r",
            reservation=self.reservation,
        )
        session = after_rental_payment_completed(p)
        data, err = preview_sign_token(session.renter_token)
        self.assertIsNone(err)
        self.assertEqual(data["your_role"], "renter")
        self.assertTrue(data["can_sign"])
        self.assertTrue(data.get("pdf_available"))

    def test_sign_renter_twice_returns_already_done(self):
        p = Payment.objects.create(
            user=self.renter,
            amount=4000,
            payment_type="rent",
            status="completed",
            transaction_id="ys_twice",
            reservation=self.reservation,
        )
        session = after_rental_payment_completed(p)
        sig = sample_signature_png()
        s1, err1 = sign_with_token(session.renter_token, signature_png_bytes=sig)
        self.assertIsNone(err1)
        s2, err2 = sign_with_token(session.renter_token, signature_png_bytes=sig)
        self.assertEqual(err2, "already_done")
        self.assertEqual(s2.pk, session.pk)

    def test_sign_rejects_too_small_png(self):
        p = Payment.objects.create(
            user=self.renter,
            amount=4000,
            payment_type="rent",
            status="completed",
            transaction_id="ys_small",
            reservation=self.reservation,
        )
        session = after_rental_payment_completed(p)
        tiny = tiny_invalid_png()
        from esign.signature_utils import MIN_SIGNATURE_BYTES

        self.assertLess(len(tiny), MIN_SIGNATURE_BYTES)
        s, err = sign_with_token(session.renter_token, signature_png_bytes=tiny)
        self.assertIsNone(s)
        self.assertEqual(err, "signature_too_small")

    def test_preview_lister_waits_for_renter(self):
        p = Payment.objects.create(
            user=self.renter,
            amount=4000,
            payment_type="rent",
            status="completed",
            transaction_id="ys_prev",
            reservation=self.reservation,
        )
        session = after_rental_payment_completed(p)
        data, err = preview_sign_token(session.lister_token)
        self.assertIsNone(err)
        self.assertEqual(data["your_role"], "lister")
        self.assertFalse(data["can_sign"])
        self.assertTrue(data.get("pdf_available"))
        self.assertIn("/esign/sign/", data.get("pdf_url", ""))


@override_settings(ESIGN_AUTO_GENERATE_CONTRACT_PDF=False)
class EsignServiceNoAutoPdfTests(TestCase):
    """Without auto-generated PDF, signing requires a lister upload first."""

    def setUp(self):
        self.area = Area.objects.create(name="Y", slug="y")
        self.lister = User.objects.create_user(
            email="lu@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.lister, role="landlord")
        LandlordProfile.objects.create(user=self.lister)
        self.renter = User.objects.create_user(
            email="ru@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.renter, role="tenant")
        self.listing = Listing.objects.create(
            title="Apt2",
            description="d",
            price=3000,
            type="apartment",
            area=self.area,
            listed_by=self.lister,
        )
        self.reservation = Reservation.objects.create(
            listing=self.listing,
            user=self.renter,
            start_date="2026-05-01",
            end_date="2027-04-30",
            status="pending",
        )

    def test_sign_without_contract_pdf_returns_error(self):
        p = Payment.objects.create(
            user=self.renter,
            amount=3000,
            payment_type="rent",
            status="completed",
            transaction_id="ys_nopdf",
            reservation=self.reservation,
        )
        session = after_rental_payment_completed(p)
        session.refresh_from_db()
        self.assertFalse(session.contract_pdf.name)
        self.assertFalse(session.lister_contract_pdf.name)
        s, err = sign_with_token(
            session.renter_token, signature_png_bytes=sample_signature_png()
        )
        self.assertEqual(err, "no_contract_pdf")

    def test_renter_cannot_sign_lister_pdf_without_signature_placements(self):
        """Realtor-uploaded PDF alone is not enough - renter rects must be saved."""
        p = Payment.objects.create(
            user=self.renter,
            amount=3000,
            payment_type="rent",
            status="completed",
            transaction_id="ys_nobox",
            reservation=self.reservation,
        )
        session = after_rental_payment_completed(p)
        raw = build_contract_pdf_bytes(self.reservation)
        session.lister_contract_pdf.save("lease.pdf", ContentFile(raw), save=False)
        session.save(update_fields=["lister_contract_pdf", "updated_at"])

        data, err = preview_sign_token(session.renter_token)
        self.assertIsNone(err)
        self.assertFalse(data["can_sign"])

        s, err = sign_with_token(
            session.renter_token, signature_png_bytes=sample_signature_png()
        )
        self.assertIsNone(s)
        self.assertEqual(err, "missing_signature_placements")

        mb = PdfReader(io.BytesIO(raw)).pages[0].mediabox
        pw, ph = float(mb.width), float(mb.height)
        session.signature_field_boxes = {
            "renter": {
                "page_index": 0,
                "x": 40,
                "y": 40,
                "width": min(120.0, pw - 80),
                "height": min(36.0, ph - 80),
            },
            "lister": {
                "page_index": 0,
                "x": 40,
                "y": 100,
                "width": min(120.0, pw - 80),
                "height": min(36.0, ph - 160),
            },
        }
        session.save(update_fields=["signature_field_boxes", "updated_at"])

        data2, err2 = preview_sign_token(session.renter_token)
        self.assertIsNone(err2)
        self.assertTrue(data2["can_sign"])

        s2, err3 = sign_with_token(
            session.renter_token, signature_png_bytes=sample_signature_png()
        )
        self.assertIsNone(err3)
        self.assertIsNotNone(s2.renter_signed_at)
