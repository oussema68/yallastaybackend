"""Tests for ReportLab / merge helpers in esign.pdf_service."""

from __future__ import annotations

import io

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from pypdf import PdfReader

from accounts.models import LandlordProfile, UserProfile
from bookings.models import Reservation
from core.models import Area
from listings.models import Listing
from payments.models import Payment

from esign.pdf_service import (
    build_contract_pdf_bytes,
    build_signature_page_bytes,
    merge_pdf_parts,
    overlay_png_on_pdf_page,
)
from esign.services import after_rental_payment_completed, sign_with_token
from esign.tests.test_services import sample_signature_png

User = get_user_model()


class PdfServicePureTests(SimpleTestCase):
    """No DB - only bytes in/out."""

    def test_merge_pdf_parts_concatenates_pages(self):
        now = timezone.now()
        p1 = build_signature_page_bytes(
            role="Renter (tenant)",
            full_name="Jane",
            email="j@example.com",
            signed_at=now,
            signature_png_bytes=None,
        )
        p2 = build_signature_page_bytes(
            role="Landlord / lister",
            full_name="Bob",
            email="b@example.com",
            signed_at=now,
            signature_png_bytes=None,
        )
        merged = merge_pdf_parts([p1, p2])
        reader = PdfReader(io.BytesIO(merged))
        self.assertEqual(len(reader.pages), 2)

    def test_overlay_png_on_pdf_page_preserves_page_count(self):
        now = timezone.now()
        one_page = build_signature_page_bytes(
            role="Renter (tenant)",
            full_name="Jane",
            email="j@example.com",
            signed_at=now,
            signature_png_bytes=sample_signature_png(),
        )
        r = PdfReader(io.BytesIO(one_page))
        mb = r.pages[0].mediabox
        pw, ph = float(mb.width), float(mb.height)
        sig = sample_signature_png()
        out = overlay_png_on_pdf_page(
            one_page,
            0,
            sig,
            x=10,
            y=10,
            width=min(80.0, pw - 20),
            height=min(40.0, ph - 20),
        )
        r2 = PdfReader(io.BytesIO(out))
        self.assertEqual(len(r2.pages), 1)
        self.assertGreater(len(out), len(one_page) // 2)

    def test_build_signature_page_with_embedded_png(self):
        sig = sample_signature_png()
        raw = build_signature_page_bytes(
            role="Renter (tenant)",
            full_name="Jane",
            email="j@example.com",
            signed_at=timezone.now(),
            signature_png_bytes=sig,
        )
        reader = PdfReader(io.BytesIO(raw))
        self.assertEqual(len(reader.pages), 1)
        self.assertGreater(len(raw), 500)


@override_settings(ESIGN_AUTO_GENERATE_CONTRACT_PDF=True)
class PdfServiceContractTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="P", slug="p")
        self.lister = User.objects.create_user(
            email="lp@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.lister, role="landlord")
        LandlordProfile.objects.create(user=self.lister)
        self.renter = User.objects.create_user(
            email="rp@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.renter, role="tenant")
        self.listing = Listing.objects.create(
            title="PdfSvc",
            description="d",
            price=2000,
            type="apartment",
            area=self.area,
            listed_by=self.lister,
        )
        self.reservation = Reservation.objects.create(
            listing=self.listing,
            user=self.renter,
            start_date="2026-07-01",
            end_date="2027-06-30",
            status="pending",
        )

    def test_build_contract_pdf_bytes_is_pdf(self):
        raw = build_contract_pdf_bytes(self.reservation)
        self.assertTrue(raw.startswith(b"%PDF"))
        reader = PdfReader(io.BytesIO(raw))
        self.assertGreaterEqual(len(reader.pages), 1)

    def test_rebuild_signed_pdf_stores_both_signatures(self):
        p = Payment.objects.create(
            user=self.renter,
            amount=2000,
            payment_type="rent",
            status="completed",
            transaction_id="ys_pdfsvc",
            reservation=self.reservation,
        )
        session = after_rental_payment_completed(p)
        self.assertIsNotNone(session)
        sig = sample_signature_png()
        s1, err1 = sign_with_token(session.renter_token, signature_png_bytes=sig)
        self.assertIsNone(err1)
        s1.refresh_from_db()
        self.assertTrue(s1.renter_signature_image.name)

        s2, err2 = sign_with_token(session.lister_token, signature_png_bytes=sig)
        self.assertIsNone(err2)
        s2.refresh_from_db()
        self.assertEqual(s2.status, "completed")
        self.assertTrue(s2.lister_signature_image.name)
        self.assertTrue(s2.signed_pdf.name)

        merged = PdfReader(io.BytesIO(s2.signed_pdf.read()))
        # Contract + renter cert + lister cert
        self.assertGreaterEqual(len(merged.pages), 2)

    def test_rebuild_signed_pdf_field_boxes_no_extra_pages(self):
        raw_contract = build_contract_pdf_bytes(self.reservation)
        base_pages = len(PdfReader(io.BytesIO(raw_contract)).pages)
        mb = PdfReader(io.BytesIO(raw_contract)).pages[0].mediabox
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
        p = Payment.objects.create(
            user=self.renter,
            amount=2000,
            payment_type="rent",
            status="completed",
            transaction_id="ys_boxmode",
            reservation=self.reservation,
        )
        session = after_rental_payment_completed(p)
        self.assertIsNotNone(session)
        session.signature_field_boxes = boxes
        session.save(update_fields=["signature_field_boxes", "updated_at"])
        sig = sample_signature_png()
        sign_with_token(session.renter_token, signature_png_bytes=sig)
        sign_with_token(session.lister_token, signature_png_bytes=sig)
        session.refresh_from_db()
        self.assertTrue(session.signed_pdf.name)
        merged = PdfReader(io.BytesIO(session.signed_pdf.read()))
        self.assertEqual(len(merged.pages), base_pages)
