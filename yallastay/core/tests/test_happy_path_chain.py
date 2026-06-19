"""
Proven happy path (stub payments): listing → reservation → pay → e-sign session → contract PDF.

Manual / Playwright steps live in ``docs/operations/happy-path-e2e-checklist.md``.
"""

from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import LandlordProfile, UserProfile, UAEIDVerification
from bookings.models import Reservation
from core.models import Area
from esign.models import LeaseSigningSession
from listings.models import Listing
from payments.models import Payment

from django.contrib.auth import get_user_model

User = get_user_model()


def _lease_dates():
    today = timezone.now().date()
    start = today + timedelta(days=7)
    end = start + timedelta(days=30)
    return start, end


@override_settings(ESIGN_AUTO_GENERATE_CONTRACT_PDF=True)
class HappyPathChainTests(TestCase):
    """API chain proving reservation + stub payment opens lease signing + PDF."""

    def setUp(self):
        self.client = APIClient()
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina-chain")
        self.landlord = User.objects.create_user(
            email="hp-landlord@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.landlord, role="landlord")
        LandlordProfile.objects.create(user=self.landlord)
        self.tenant = User.objects.create_user(
            email="hp-tenant@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.tenant, role="tenant")
        UAEIDVerification.objects.create(
            user=self.tenant, id_hash="happy_path_uae", status="approved"
        )
        self.listing = Listing.objects.create(
            title="Happy Path Apt",
            description="E2E chain",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=self.landlord,
        )

    def test_reservation_rent_pay_stub_opens_esign_and_contract_pdf(self):
        start, end = _lease_dates()
        self.client.force_authenticate(user=self.tenant)
        r = self.client.post(
            "/api/reservations/",
            {
                "listing_id": self.listing.id,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        reservation = Reservation.objects.get(user=self.tenant, listing=self.listing)

        pay = self.client.post(
            "/api/payments/initiate/",
            {
                "amount": "5000.00",
                "payment_type": "rent",
                "currency": "AED",
                "reservation_id": reservation.id,
            },
            format="json",
        )
        self.assertEqual(pay.status_code, status.HTTP_201_CREATED, pay.data)
        self.assertEqual(pay.data.get("provider"), "stub")
        tid = pay.data["transaction_id"]

        wh = self.client.post(
            "/api/payments/webhook/stub/",
            {"transaction_id": tid},
            format="json",
        )
        self.assertEqual(wh.status_code, status.HTTP_200_OK)

        pmt = Payment.objects.get(transaction_id=tid)
        self.assertEqual(pmt.status, "completed")
        session = LeaseSigningSession.objects.get(reservation=reservation)
        self.assertEqual(session.triggering_payment_id, pmt.id)
        self.assertTrue(session.contract_pdf or session.lister_contract_pdf)

        pdf = self.client.get(f"/api/esign/sessions/{session.id}/contract-pdf/")
        self.assertEqual(pdf.status_code, status.HTTP_200_OK)
        self.assertEqual(pdf["Content-Type"], "application/pdf")

        dash = self.client.get("/api/esign/sessions/")
        self.assertEqual(dash.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in dash.data]
        self.assertIn(session.id, ids)
