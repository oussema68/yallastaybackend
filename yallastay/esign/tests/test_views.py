import base64
import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from pypdf import PdfReader
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import LandlordProfile, UserProfile
from bookings.models import Reservation
from core.models import Area
from listings.models import Listing
from payments.models import Payment

from esign.pdf_service import build_contract_pdf_bytes
from esign.services import after_rental_payment_completed
from esign.signature_utils import MIN_SIGNATURE_BYTES
from esign.tests.test_services import sample_signature_png, tiny_invalid_png

User = get_user_model()


def _sign_post(**fields):
    """POST body for magic-link sign; UAE flow requires consent on first sign per party."""
    return {"consent_to_electronic_signature": True, **fields}


@override_settings(ESIGN_AUTO_GENERATE_CONTRACT_PDF=True)
class EsignViewTests(APITestCase):
    """Each test that signs uses a fresh session via `_make_session` (order-independent)."""

    def setUp(self):
        self.area = Area.objects.create(name="X", slug="x")
        self.lister = User.objects.create_user(
            email="lv@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.lister, role="landlord")
        LandlordProfile.objects.create(user=self.lister)
        self.renter = User.objects.create_user(
            email="rv@example.com", password="Pass123!"
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

    def _make_session(self, transaction_id: str):
        reservation = Reservation.objects.create(
            listing=self.listing,
            user=self.renter,
            start_date="2026-05-01",
            end_date="2027-04-30",
            status="pending",
        )
        p = Payment.objects.create(
            user=self.renter,
            amount=4000,
            payment_type="rent",
            status="completed",
            transaction_id=transaction_id,
            reservation=reservation,
        )
        return after_rental_payment_completed(p)

    def test_list_requires_auth(self):
        r = self.client.get("/api/esign/sessions/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sign_token_no_auth(self):
        session = self._make_session("ys_v_sign")
        b64 = base64.b64encode(sample_signature_png()).decode("ascii")
        r = self.client.post(
            f"/api/esign/sign/{session.renter_token}/",
            _sign_post(signature_png=b64),
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["session"]["status"], "pending")

    def test_sign_without_signature_png_returns_400(self):
        session = self._make_session("ys_v_empty")
        r = self.client.post(
            f"/api/esign/sign/{session.renter_token}/",
            _sign_post(),
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", r.data)

    def test_list_authenticated_renter(self):
        self._make_session("ys_v_list")
        self.client.force_authenticate(user=self.renter)
        r = self.client.get("/api/esign/sessions/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        self.assertIn("my_sign_url", r.data[0])
        self.assertEqual(r.data[0]["viewer_role"], "renter")
        self.assertIn("instructions", r.data[0])

    def test_get_sign_preview_no_auth(self):
        session = self._make_session("ys_v_prev")
        r = self.client.get(f"/api/esign/sign/{session.renter_token}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["your_role"], "renter")
        self.assertTrue(r.data["can_sign"])
        self.assertTrue(r.data.get("pdf_available"))

    def test_get_sign_pdf_no_auth(self):
        session = self._make_session("ys_v_pdf")
        r = self.client.get(f"/api/esign/sign/{session.renter_token}/pdf/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r["Content-Type"], "application/pdf")
        # Must not send DENY - otherwise the PDF cannot load in an iframe on the signing page.
        self.assertNotEqual(r.get("X-Frame-Options"), "DENY")

    def test_list_includes_pdf_api_url(self):
        self._make_session("ys_v_pdfurl")
        self.client.force_authenticate(user=self.renter)
        r = self.client.get("/api/esign/sessions/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("/esign/sign/", r.data[0].get("pdf_api_url", ""))

    def test_session_contract_pdf_requires_auth(self):
        session = self._make_session("ys_v_sesspdf_auth")
        r = self.client.get(f"/api/esign/sessions/{session.pk}/contract-pdf/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_session_contract_pdf_authenticated_returns_pdf(self):
        session = self._make_session("ys_v_sesspdf_ok")
        self.client.force_authenticate(user=self.renter)
        r = self.client.get(f"/api/esign/sessions/{session.pk}/contract-pdf/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r["Content-Type"], "application/pdf")

    def test_lister_sign_before_renter_returns_400(self):
        session = self._make_session("ys_v_lister")
        r = self.client.post(
            f"/api/esign/sign/{session.lister_token}/",
            _sign_post(
                signature_png=base64.b64encode(sample_signature_png()).decode("ascii")
            ),
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("renter", r.data["detail"].lower())

    def test_sign_accepts_data_url_payload(self):
        session = self._make_session("ys_v_dataurl")
        raw = sample_signature_png()
        data_url = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
        r = self.client.post(
            f"/api/esign/sign/{session.renter_token}/",
            _sign_post(signature_png=data_url),
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_sign_too_small_returns_400_with_code(self):
        session = self._make_session("ys_v_small")
        tiny = tiny_invalid_png()
        self.assertLess(len(tiny), MIN_SIGNATURE_BYTES)
        r = self.client.post(
            f"/api/esign/sign/{session.renter_token}/",
            _sign_post(signature_png=base64.b64encode(tiny).decode("ascii")),
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data.get("code"), "signature_too_small")

    def test_sign_renter_second_post_returns_already_signed(self):
        session = self._make_session("ys_v_twice")
        b64 = base64.b64encode(sample_signature_png()).decode("ascii")
        url = f"/api/esign/sign/{session.renter_token}/"
        r1 = self.client.post(url, _sign_post(signature_png=b64), format="json")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        r2 = self.client.post(url, {"signature_png": b64}, format="json")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertIn("already", r2.data["detail"].lower())

    def test_get_preview_after_renter_signed_shows_progress(self):
        session = self._make_session("ys_v_after")
        b64 = base64.b64encode(sample_signature_png()).decode("ascii")
        self.client.post(
            f"/api/esign/sign/{session.renter_token}/",
            _sign_post(signature_png=b64),
            format="json",
        )
        r = self.client.get(f"/api/esign/sign/{session.renter_token}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["can_sign"])
        self.assertTrue(r.data["renter_signed"])
        self.assertFalse(r.data["lister_signed"])


@override_settings(ESIGN_AUTO_GENERATE_CONTRACT_PDF=False)
class EsignUploadContractViewTests(APITestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Z", slug="z")
        self.lister = User.objects.create_user(
            email="up@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.lister, role="landlord")
        LandlordProfile.objects.create(user=self.lister)
        self.renter = User.objects.create_user(
            email="ur@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.renter, role="tenant")
        self.listing = Listing.objects.create(
            title="UpTest",
            description="d",
            price=3500,
            type="apartment",
            area=self.area,
            listed_by=self.lister,
        )
        self.reservation = Reservation.objects.create(
            listing=self.listing,
            user=self.renter,
            start_date="2026-06-01",
            end_date="2027-05-31",
            status="pending",
        )
        p = Payment.objects.create(
            user=self.renter,
            amount=3500,
            payment_type="rent",
            status="completed",
            transaction_id="ys_up",
            reservation=self.reservation,
        )
        self.session = after_rental_payment_completed(p)

    def test_lister_uploads_pdf_then_preview_available(self):
        self.client.force_authenticate(user=self.lister)
        raw = build_contract_pdf_bytes(self.reservation)
        upload = SimpleUploadedFile("lease.pdf", raw, content_type="application/pdf")
        r = self.client.post(
            f"/api/esign/sessions/{self.session.pk}/upload-contract/",
            {"file": upload},
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data.get("contract_pdf_ready"))
        self.assertFalse(r.data.get("needs_lister_contract_upload"))

        prev = self.client.get(f"/api/esign/sign/{self.session.renter_token}/")
        self.assertEqual(prev.status_code, status.HTTP_200_OK)
        self.assertFalse(prev.data["can_sign"])
        self.assertIn("signature field", (prev.data.get("message") or "").lower())

        sign_blocked = self.client.post(
            f"/api/esign/sign/{self.session.renter_token}/",
            _sign_post(
                signature_png=base64.b64encode(sample_signature_png()).decode("ascii")
            ),
            format="json",
        )
        self.assertEqual(sign_blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(sign_blocked.data.get("code"), "missing_signature_placements")

        mb = PdfReader(io.BytesIO(raw)).pages[0].mediabox
        pw, ph = float(mb.width), float(mb.height)
        boxes = {
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
        patch_r = self.client.patch(
            f"/api/esign/sessions/{self.session.pk}/signature-fields/",
            {"signature_field_boxes": boxes},
            format="json",
        )
        self.assertEqual(patch_r.status_code, status.HTTP_200_OK)

        prev2 = self.client.get(f"/api/esign/sign/{self.session.renter_token}/")
        self.assertTrue(prev2.data["can_sign"])

        pdf_r = self.client.get(f"/api/esign/sign/{self.session.renter_token}/pdf/")
        self.assertEqual(pdf_r.status_code, status.HTTP_200_OK)

        sign_r = self.client.post(
            f"/api/esign/sign/{self.session.renter_token}/",
            _sign_post(
                signature_png=base64.b64encode(sample_signature_png()).decode("ascii")
            ),
            format="json",
        )
        self.assertEqual(sign_r.status_code, status.HTTP_200_OK)
